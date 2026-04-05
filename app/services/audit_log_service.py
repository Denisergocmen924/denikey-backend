from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.audit_log import AuditLog
import uuid


async def create_audit_log(
    db: AsyncSession,
    user_id: str,
    action: str,
    status: str,
    ip_address: str = None,
    extra_data: dict = None,
) -> None:
    log = AuditLog(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        action=action,
        status=status,
        ip_address=ip_address,
        extra_data=extra_data,
    )
    db.add(log)
    await db.flush()


async def get_audit_logs(db: AsyncSession, user_id: str) -> list:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == uuid.UUID(user_id))
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id),
            "action": log.action,
            "ip_address": log.ip_address,
            "status": log.status,
            "extra_data": log.extra_data,
            "created_at": log.created_at,
        }
        for log in logs
    ]
