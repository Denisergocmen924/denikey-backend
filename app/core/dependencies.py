from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.core.security import verify_access_token
from app.models.user import User
from app.services.device_service import check_and_update_device

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz token içeriği"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı"
        )

    # Logout sonrası token geçersizleştirme kontrolü
    if payload.get("tv") != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum sonlandırılmış, lütfen tekrar giriş yapın",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız kilitlenmiştir"
        )

    # Cihaz durumu kontrolü
    device_id = payload.get("did")
    if device_id:
        device_status = await check_and_update_device(db, user_id, device_id)
        # None = cihaz kalıcı silinmiş; token'ı geçersiz say (revoked gibi davran)
        if device_status is None or device_status in ("revoked", "banned"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bu cihazın oturumu sonlandırılmış, lütfen tekrar giriş yapın",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user


async def get_current_device_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _verified_user: User = Depends(get_current_user),
) -> str:
    """JWT içindeki cihaz kimliğini döndürür; doğrulama get_current_user üzerinden yapılır."""
    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz token")
    return payload.get("did", "")
