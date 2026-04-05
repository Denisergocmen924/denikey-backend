from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.audit_log_service import get_audit_logs

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

@router.get("/")
async def get_my_audit_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logs = await get_audit_logs(db, str(current_user.id))
    return logs
