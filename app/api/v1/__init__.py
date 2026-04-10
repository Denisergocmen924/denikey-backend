from fastapi import APIRouter
from app.api.v1.endpoints import auth, vault, category, password, audit_log, support_ticket, trash, item_type

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(vault.router)
router.include_router(category.router)
router.include_router(password.router)
router.include_router(audit_log.router)
router.include_router(support_ticket.router)
router.include_router(trash.router)
router.include_router(item_type.router)
