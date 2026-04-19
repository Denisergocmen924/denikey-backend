import resend
import random
import string
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.verification_code import VerificationCode
from app.core.config import settings
import uuid

resend.api_key = settings.RESEND_API_KEY


def _generate_code() -> str:
    return ''.join(random.choices(string.digits, k=6))


async def send_verification_code(
    db: AsyncSession,
    user_id: str,
    email: str,
    purpose: str,
) -> bool:
    # Eski kodları geçersiz kıl
    result = await db.execute(
        select(VerificationCode).where(
            VerificationCode.user_id == uuid.UUID(user_id),
            VerificationCode.purpose == purpose,
            VerificationCode.is_used == False,
        )
    )
    old_codes = result.scalars().all()
    for old in old_codes:
        old.is_used = True
    await db.flush()

    # Yeni kod oluştur
    code = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    verification = VerificationCode(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        code=code,
        purpose=purpose,
        is_used=False,
        expires_at=expires_at,
    )
    db.add(verification)
    await db.flush()

    # Mail gönder
    subject_map = {
        "register": "DeniKey — Hesabınızı doğrulayın",
        "new_device": "DeniKey — Yeni cihaz girişi",
        "forgot_password": "DeniKey — Şifre sıfırlama",
        "email_change": "DeniKey — E-posta değişikliği",
    }

    body_map = {
        "register": f"Hesabınızı doğrulamak için kodunuz: <b>{code}</b><br>Bu kod 10 dakika geçerlidir.",
        "new_device": f"Yeni cihaz girişi tespit edildi. Doğrulama kodunuz: <b>{code}</b><br>Bu kod 10 dakika geçerlidir.",
        "forgot_password": f"Şifrenizi sıfırlamak için kodunuz: <b>{code}</b><br>Bu kod 10 dakika geçerlidir.",
        "email_change": f"E-posta değişikliği için doğrulama kodunuz: <b>{code}</b><br>Bu kod 10 dakika geçerlidir.",
    }

    try:
        resend.Emails.send({
            "from": "noreply@denikey.website",
            "to": email,
            "subject": subject_map.get(purpose, "DeniKey — Doğrulama kodu"),
            "html": f"""
                <div style="font-family: sans-serif; max-width: 400px; margin: 0 auto;">
                    <h2 style="color: #534AB7;">DeniKey</h2>
                    <p>{body_map.get(purpose, f'Doğrulama kodunuz: <b>{code}</b>')}</p>
                    <div style="background: #f5f5f5; padding: 16px; border-radius: 8px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #534AB7;">
                        {code}
                    </div>
                    <p style="color: #888; font-size: 12px; margin-top: 16px;">Bu maili siz istemediyseniz dikkate almayın.</p>
                </div>
            """,
        })
        return True
    except Exception:
        return False


async def verify_code(
    db: AsyncSession,
    user_id: str,
    code: str,
    purpose: str,
) -> bool:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(VerificationCode).where(
            VerificationCode.user_id == uuid.UUID(user_id),
            VerificationCode.code == code,
            VerificationCode.purpose == purpose,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > now,
        )
    )
    verification = result.scalar_one_or_none()

    if not verification:
        return False

    verification.is_used = True
    await db.flush()
    return True


async def send_support_reply(user_email: str, subject: str, reply_text: str) -> bool:
    try:
        resend.Emails.send({
            "from": "noreply@denikey.website",
            "to": user_email,
            "subject": f"DeniKey Destek — {subject}",
            "html": f"""
                <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto;">
                    <h2 style="color: #534AB7;">DeniKey Destek</h2>
                    <p>Destek talebinize yanıt verildi:</p>
                    <div style="background: #f5f5f5; padding: 16px; border-radius: 8px; border-left: 4px solid #534AB7; white-space: pre-wrap;">
                        {reply_text}
                    </div>
                    <p style="color: #888; font-size: 12px; margin-top: 16px;">DeniKey Destek Ekibi</p>
                </div>
            """,
        })
        return True
    except Exception:
        return False


async def send_account_deletion_notification(email: str) -> bool:
    try:
        resend.Emails.send({
            "from": "noreply@denikey.website",
            "to": email,
            "subject": "DeniKey — Hesabınız kalıcı olarak silindi",
            "html": """
                <div style="font-family: sans-serif; max-width: 400px; margin: 0 auto;">
                    <h2 style="color: #534AB7;">DeniKey</h2>
                    <p>Hesabınız ve hesabınıza ait tüm veriler <b>kalıcı olarak silinmiştir</b>.</p>
                    <p>DeniKey'i kullandığınız için teşekkür ederiz.</p>
                    <p>Bu işlemi siz yapmadıysanız lütfen bizimle iletişime geçin.</p>
                    <p style="color: #888; font-size: 12px;">DeniKey Güvenlik Ekibi</p>
                </div>
            """,
        })
        return True
    except Exception:
        return False


async def send_email_change_notification(old_email: str) -> bool:
    try:
        resend.Emails.send({
            "from": "noreply@denikey.website",
            "to": old_email,
            "subject": "DeniKey — E-posta adresiniz değiştirildi",
            "html": """
                <div style="font-family: sans-serif; max-width: 400px; margin: 0 auto;">
                    <h2 style="color: #534AB7;">DeniKey</h2>
                    <p>Hesabınıza bağlı e-posta adresi değiştirildi.</p>
                    <p>Bu işlemi siz yapmadıysanız lütfen hemen bizimle iletişime geçin.</p>
                    <p style="color: #888; font-size: 12px;">DeniKey Güvenlik Ekibi</p>
                </div>
            """,
        })
        return True
    except Exception:
        return False
