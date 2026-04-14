from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.database import get_db
from app.models.support_ticket import SupportTicket
from app.models.user import User
from app.services.email_service import send_support_reply
from app.core.config import settings
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
import uuid

router = APIRouter(prefix="/admin", tags=["Admin"])


def _require_admin(x_admin_key: str = Header(...)):
    if x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz admin anahtarı")


def _serialize(ticket: SupportTicket, email: str) -> dict:
    return {
        "id": str(ticket.id),
        "user_id": str(ticket.user_id),
        "user_email": email,
        "category": ticket.category,
        "subject": ticket.subject,
        "message": ticket.message,
        "priority": ticket.priority,
        "status": ticket.status,
        "admin_reply": ticket.admin_reply,
        "replied_at": ticket.replied_at.isoformat() if ticket.replied_at else None,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }


@router.get("/tickets")
async def list_tickets(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    query = select(SupportTicket, User.email).join(User, SupportTicket.user_id == User.id)
    if status_filter and status_filter != "all":
        query = query.where(SupportTicket.status == status_filter)
    query = query.order_by(SupportTicket.created_at.desc())
    result = await db.execute(query)
    rows = result.all()
    return [_serialize(t, email) for t, email in rows]


@router.get("/tickets/stats")
async def ticket_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(
        select(SupportTicket.status, func.count().label("count"))
        .group_by(SupportTicket.status)
    )
    rows = result.all()
    stats = {"open": 0, "in_progress": 0, "closed": 0, "total": 0}
    for s, c in rows:
        if s in stats:
            stats[s] = c
        stats["total"] += c
    return stats


class ReplyBody(BaseModel):
    reply: str
    close_after: bool = False


@router.post("/tickets/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: str,
    body: ReplyBody,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(
        select(SupportTicket, User.email)
        .join(User, SupportTicket.user_id == User.id)
        .where(SupportTicket.id == uuid.UUID(ticket_id))
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Ticket bulunamadı")

    ticket, email = row
    ticket.admin_reply = body.reply
    ticket.replied_at = datetime.now(timezone.utc)
    if body.close_after:
        ticket.status = "closed"
    elif ticket.status == "open":
        ticket.status = "in_progress"

    await send_support_reply(email, ticket.subject, body.reply)
    await db.commit()
    await db.refresh(ticket)
    return _serialize(ticket, email)


class StatusBody(BaseModel):
    status: str  # open | in_progress | closed


@router.patch("/tickets/{ticket_id}/status")
async def update_status(
    ticket_id: str,
    body: StatusBody,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    if body.status not in ("open", "in_progress", "closed"):
        raise HTTPException(status_code=400, detail="Geçersiz durum")
    result = await db.execute(
        select(SupportTicket, User.email)
        .join(User, SupportTicket.user_id == User.id)
        .where(SupportTicket.id == uuid.UUID(ticket_id))
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Ticket bulunamadı")

    ticket, email = row
    ticket.status = body.status
    await db.commit()
    await db.refresh(ticket)
    return _serialize(ticket, email)
