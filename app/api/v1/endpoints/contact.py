import uuid
from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.ratelimit import get_client_ip
from app.models.website_contact import WebsiteContact
from app.schemas.website_contact import WebsiteContactCreate
from app.services.email_service import send_contact_notification

router = APIRouter(prefix="/contact", tags=["Contact"])
limiter = Limiter(key_func=get_client_ip)


@router.post("")
@limiter.limit("5/hour")
async def create_contact(
    request: Request,
    payload: WebsiteContactCreate,
    db: AsyncSession = Depends(get_db),
):
    contact = WebsiteContact(
        id=uuid.uuid4(),
        type=payload.type,
        name=payload.name,
        email=payload.email,
        subject=payload.subject,
        message=payload.message,
        status="new",
    )
    db.add(contact)
    await db.commit()
    # commit sonrası ORM nesnesinin alanları expire olur; bildirim arka planda
    # (session kapandıktan sonra) çalıştığı için session'a bağlı olmayan payload geçilir.
    await send_contact_notification(payload)
    return {"ok": True}
