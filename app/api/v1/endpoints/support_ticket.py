from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.support_ticket import SupportTicketCreate, SupportTicketResponse
from app.services.support_ticket_service import (
    create_ticket,
    get_my_tickets,
    get_ticket,
    close_ticket,
)
from typing import List

router = APIRouter(prefix="/support-ticket", tags=["Support Tickets"])


@router.post("/", response_model=SupportTicketResponse)
async def create_support_ticket(
    data: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_ticket(db, data, current_user)


@router.get("/", response_model=List[SupportTicketResponse])
async def get_support_tickets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_my_tickets(db, current_user)


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
async def get_support_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_ticket(db, ticket_id, current_user)


@router.patch("/{ticket_id}/close", response_model=SupportTicketResponse)
async def close_support_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await close_ticket(db, ticket_id, current_user)
