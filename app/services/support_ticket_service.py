from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.support_ticket import SupportTicket
from app.schemas.support_ticket import SupportTicketCreate
from app.models.user import User
from fastapi import HTTPException, status
import uuid


async def create_ticket(
    db: AsyncSession,
    data: SupportTicketCreate,
    current_user: User,
) -> dict:
    ticket = SupportTicket(
        id=uuid.uuid4(),
        user_id=current_user.id,
        category=data.category,
        subject=data.subject,
        message=data.message,
        priority=data.priority,
        status="open",
    )
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket)
    return _serialize(ticket)


async def get_my_tickets(db: AsyncSession, current_user: User) -> list:
    result = await db.execute(
        select(SupportTicket)
        .where(SupportTicket.user_id == current_user.id)
        .order_by(SupportTicket.created_at.desc())
    )
    tickets = result.scalars().all()
    return [_serialize(t) for t in tickets]


async def get_ticket(db: AsyncSession, ticket_id: str, current_user: User) -> dict:
    result = await db.execute(
        select(SupportTicket)
        .where(
            SupportTicket.id == uuid.UUID(ticket_id),
            SupportTicket.user_id == current_user.id,
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket bulunamadı")
    return _serialize(ticket)


async def delete_ticket(db: AsyncSession, ticket_id: str, current_user: User) -> None:
    result = await db.execute(
        select(SupportTicket)
        .where(
            SupportTicket.id == uuid.UUID(ticket_id),
            SupportTicket.user_id == current_user.id,
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket bulunamadı")
    await db.delete(ticket)
    await db.flush()


async def close_ticket(db: AsyncSession, ticket_id: str, current_user: User) -> dict:
    result = await db.execute(
        select(SupportTicket)
        .where(
            SupportTicket.id == uuid.UUID(ticket_id),
            SupportTicket.user_id == current_user.id,
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket bulunamadı")
    if ticket.status == "closed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticket zaten kapalı")

    ticket.status = "closed"
    await db.flush()
    await db.refresh(ticket)
    return _serialize(ticket)


def _serialize(ticket: SupportTicket) -> dict:
    return {
        "id": str(ticket.id),
        "user_id": str(ticket.user_id),
        "category": ticket.category,
        "subject": ticket.subject,
        "message": ticket.message,
        "priority": ticket.priority,
        "status": ticket.status,
        "admin_reply": ticket.admin_reply,
        "replied_at": ticket.replied_at,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
    }
