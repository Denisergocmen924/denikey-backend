from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, text
from app.db.database import get_db
from app.models.support_ticket import SupportTicket
from app.models.website_contact import WebsiteContact
from app.models.user import User
from app.models.device import Device
from app.models.audit_log import AuditLog
from app.models.vault_item import VaultItem
from app.models.system_setting import SystemSetting
from app.services.email_service import send_support_reply
from app.core.config import settings
from app.api.v1.endpoints.version import clear_version_cache
from pydantic import BaseModel
from datetime import datetime, timezone, date, timedelta
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
import uuid
import secrets

router = APIRouter(prefix="/admin", tags=["Admin"])
limiter = Limiter(key_func=get_remote_address)


def _require_admin(x_admin_key: str = Header(...)):
    if not secrets.compare_digest(x_admin_key.encode(), settings.ADMIN_SECRET_KEY.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz admin anahtarı")


# --- Ticket yardımcıları ---

def _serialize_ticket(ticket: SupportTicket, email: str) -> dict:
    return {
        "id": str(ticket.id),
        "user_id": str(ticket.user_id),
        "user_email": email,
        "category": ticket.category,
        "subject": ticket.subject,
        "message": ticket.message,
        "priority": ticket.priority,
        "status": ticket.status,
        "is_archived": ticket.is_archived,
        "admin_reply": ticket.admin_reply,
        "replied_at": ticket.replied_at.isoformat() if ticket.replied_at else None,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }


# --- Dashboard ---

@router.get("/dashboard")
@limiter.limit("30/minute")
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    verified_users = (await db.execute(select(func.count()).select_from(User).where(User.is_verified == True))).scalar()
    locked_users = (await db.execute(select(func.count()).select_from(User).where(User.is_locked == True))).scalar()
    today_registered = (await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= today_start)
    )).scalar()
    total_vault_items = (await db.execute(select(func.count()).select_from(VaultItem))).scalar()
    open_tickets = (await db.execute(
        select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "open")
    )).scalar()

    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "locked_users": locked_users,
        "today_registered": today_registered,
        "total_vault_items": total_vault_items,
        "open_tickets": open_tickets,
    }


# --- Kullanıcı Yönetimi ---

@router.get("/users")
@limiter.limit("30/minute")
async def list_users(
    request: Request,
    search: Optional[str] = None,
    page: int = 0,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    query = select(User).order_by(desc(User.created_at))
    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    query = query.offset(page * 20).limit(20)
    users = (await db.execute(query)).scalars().all()

    return {
        "total": total,
        "page": page,
        "users": [
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "is_verified": u.is_verified,
                "is_locked": u.is_locked,
                "totp_enabled": u.totp_enabled,
                "auth_hash_version": u.auth_hash_version,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.get("/users/{user_id}")
@limiter.limit("30/minute")
async def get_user(
    request: Request,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    devices_result = await db.execute(
        select(Device).where(Device.user_id == user_id).order_by(desc(Device.last_active_at))
    )
    devices = devices_result.scalars().all()

    logs_result = await db.execute(
        select(AuditLog).where(AuditLog.user_id == user_id).order_by(desc(AuditLog.created_at)).limit(15)
    )
    logs = logs_result.scalars().all()

    vault_count = (await db.execute(
        select(func.count()).select_from(VaultItem).where(VaultItem.user_id == user_id)
    )).scalar()

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_verified": user.is_verified,
        "is_locked": user.is_locked,
        "failed_attempts": user.failed_attempts,
        "totp_enabled": user.totp_enabled,
        "auth_hash_version": user.auth_hash_version,
        "preferred_language": user.preferred_language,
        "preferred_theme": user.preferred_theme,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "vault_item_count": vault_count,
        "devices": [
            {
                "id": str(d.id),
                "display_name": d.display_name or d.device_name,
                "device_type": d.device_type,
                "status": d.status,
                "is_trusted": d.is_trusted,
                "ip_address": d.ip_address,
                "last_active_at": d.last_active_at.isoformat() if d.last_active_at else None,
            }
            for d in devices
        ],
        "recent_logs": [
            {
                "action": log.action,
                "status": log.status,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.post("/users/{user_id}/ban")
@limiter.limit("20/minute")
async def ban_user(
    request: Request,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    user.is_locked = True
    user.token_version = (user.token_version or 0) + 1  # tüm aktif oturumları geçersiz kıl
    await db.commit()
    return {"message": "Kullanıcı yasaklandı"}


@router.post("/users/{user_id}/unban")
@limiter.limit("20/minute")
async def unban_user(
    request: Request,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    user.is_locked = False
    user.failed_attempts = 0
    user.lock_until = None
    await db.commit()
    return {"message": "Kullanıcı yasağı kaldırıldı"}


@router.delete("/users/{user_id}")
@limiter.limit("10/minute")
async def delete_user(
    request: Request,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    await db.delete(user)
    await db.commit()
    return {"message": "Kullanıcı silindi"}


# --- Audit Log ---

@router.get("/audit-logs")
@limiter.limit("30/minute")
async def list_audit_logs(
    request: Request,
    page: int = 0,
    user_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    query = (
        select(AuditLog, User.username, User.email)
        .join(User, AuditLog.user_id == User.id)
        .order_by(desc(AuditLog.created_at))
    )
    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    query = query.offset(page * 50).limit(50)
    rows = (await db.execute(query)).all()

    return {
        "total": total,
        "page": page,
        "logs": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "username": username,
                "email": email,
                "action": log.action,
                "status": log.status,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log, username, email in rows
        ],
    }


# --- Versiyon Yönetimi ---

@router.get("/version")
@limiter.limit("30/minute")
async def get_version(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "minimum_app_version")
    )
    setting = result.scalar_one_or_none()
    value = setting.value if setting else settings.MINIMUM_APP_VERSION
    return {"version": value}


class VersionBody(BaseModel):
    version: str


@router.put("/version")
@limiter.limit("10/minute")
async def update_version(
    request: Request,
    body: VersionBody,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "minimum_app_version")
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = body.version
    else:
        db.add(SystemSetting(key="minimum_app_version", value=body.version))
    await db.commit()
    clear_version_cache()
    return {"version": body.version}


# --- Ticket Yönetimi ---

@router.get("/tickets")
@limiter.limit("30/minute")
async def list_tickets(
    request: Request,
    status_filter: Optional[str] = None,
    show_archived: bool = False,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    query = select(SupportTicket, User.email).join(User, SupportTicket.user_id == User.id)
    if not show_archived:
        query = query.where(SupportTicket.is_archived == False)
    if status_filter and status_filter != "all":
        query = query.where(SupportTicket.status == status_filter)
    query = query.order_by(SupportTicket.created_at.desc())
    result = await db.execute(query)
    rows = result.all()
    return [_serialize_ticket(t, email) for t, email in rows]


@router.get("/tickets/stats")
@limiter.limit("30/minute")
async def ticket_stats(
    request: Request,
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
@limiter.limit("20/minute")
async def reply_ticket(
    request: Request,
    ticket_id: uuid.UUID,
    body: ReplyBody,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(
        select(SupportTicket, User.email)
        .join(User, SupportTicket.user_id == User.id)
        .where(SupportTicket.id == ticket_id)
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
    return _serialize_ticket(ticket, email)


class ArchiveBody(BaseModel):
    is_archived: bool


@router.patch("/tickets/{ticket_id}/archive")
@limiter.limit("20/minute")
async def archive_ticket(
    request: Request,
    ticket_id: uuid.UUID,
    body: ArchiveBody,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(
        select(SupportTicket, User.email)
        .join(User, SupportTicket.user_id == User.id)
        .where(SupportTicket.id == ticket_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Ticket bulunamadı")
    ticket, email = row
    ticket.is_archived = body.is_archived
    await db.commit()
    await db.refresh(ticket)
    return _serialize_ticket(ticket, email)


class StatusBody(BaseModel):
    status: str


@router.patch("/tickets/{ticket_id}/status")
@limiter.limit("20/minute")
async def update_status(
    request: Request,
    ticket_id: uuid.UUID,
    body: StatusBody,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    if body.status not in ("open", "in_progress", "closed"):
        raise HTTPException(status_code=400, detail="Geçersiz durum")
    result = await db.execute(
        select(SupportTicket, User.email)
        .join(User, SupportTicket.user_id == User.id)
        .where(SupportTicket.id == ticket_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Ticket bulunamadı")
    ticket, email = row
    ticket.status = body.status
    await db.commit()
    await db.refresh(ticket)
    return _serialize_ticket(ticket, email)


# --- Website İletişim ---

def _serialize_contact(c: WebsiteContact) -> dict:
    return {
        "id": str(c.id),
        "type": c.type,
        "name": c.name,
        "email": c.email,
        "subject": c.subject,
        "message": c.message,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/contacts")
@limiter.limit("30/minute")
async def list_contacts(
    request: Request,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 0,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    q = select(WebsiteContact).order_by(desc(WebsiteContact.created_at))
    if type_filter:
        q = q.where(WebsiteContact.type == type_filter)
    if status_filter:
        q = q.where(WebsiteContact.status == status_filter)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.offset(page * 20).limit(20))).scalars().all()
    return {"total": total, "contacts": [_serialize_contact(c) for c in rows]}


@router.get("/contacts/stats")
@limiter.limit("30/minute")
async def contact_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    new_count = (await db.execute(
        select(func.count()).select_from(WebsiteContact).where(WebsiteContact.status == "new")
    )).scalar()
    return {"new": new_count}


class ContactStatusBody(BaseModel):
    status: str


@router.patch("/contacts/{contact_id}/status")
@limiter.limit("20/minute")
async def update_contact_status(
    request: Request,
    contact_id: uuid.UUID,
    body: ContactStatusBody,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    if body.status not in ("new", "read", "closed"):
        raise HTTPException(status_code=400, detail="Geçersiz durum")
    c = (await db.execute(
        select(WebsiteContact).where(WebsiteContact.id == contact_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="İletişim kaydı bulunamadı")
    c.status = body.status
    await db.commit()
    await db.refresh(c)
    return _serialize_contact(c)


@router.delete("/contacts/{contact_id}")
@limiter.limit("20/minute")
async def delete_contact(
    request: Request,
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    c = (await db.execute(
        select(WebsiteContact).where(WebsiteContact.id == contact_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="İletişim kaydı bulunamadı")
    await db.delete(c)
    await db.commit()
    return {"ok": True}
