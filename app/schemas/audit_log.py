from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    action: str
    ip_address: Optional[str] = None
    status: str
    extra_data: Optional[Any] = None
    created_at: datetime

    model_config = {"from_attributes": True}
