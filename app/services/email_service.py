import asyncio
import logging
import resend
import secrets
import string
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.verification_code import VerificationCode
from app.core.config import settings
import uuid

resend.api_key = settings.RESEND_API_KEY

logger = logging.getLogger(__name__)


def _generate_code() -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(6))


async def _fire_resend(payload: dict) -> None:
    """resend.Emails.send() senkron bir HTTP çağrısıdır; thread pool'da çalıştırarak
    asyncio event loop'unu bloke etmekten kaçınır."""
    try:
        await asyncio.to_thread(resend.Emails.send, payload)
    except Exception as e:
        logger.error("Resend e-posta gönderilemedi — to=%s subject=%s hata=%s",
                     payload.get("to"), payload.get("subject"), e)


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
        target_email=email,
        is_used=False,
        expires_at=expires_at,
    )
    db.add(verification)
    await db.flush()

    # Mail arka planda gönderilir; kayıt/giriş yanıtını bloke etmez.
    subject_map = {
        "register": "DeniKey — Hesabınızı doğrulayın",
        "new_device": "DeniKey — Yeni cihaz girişi",
        "email_change": "DeniKey — E-posta değişikliği",
    }

    body_map = {
        "register": f"Hesabınızı doğrulamak için kodunuz: <b>{code}</b><br>Bu kod 10 dakika geçerlidir.",
        "new_device": f"Yeni cihaz girişi tespit edildi. Doğrulama kodunuz: <b>{code}</b><br>Bu kod 10 dakika geçerlidir.",
        "email_change": f"E-posta değişikliği için doğrulama kodunuz: <b>{code}</b><br>Bu kod 10 dakika geçerlidir.",
    }

    asyncio.create_task(_fire_resend({
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
    }))
    return True


async def verify_code(
    db: AsyncSession,
    user_id: str,
    code: str,
    purpose: str,
    target_email: str = None,
) -> bool:
    now = datetime.now(timezone.utc)
    # order_by + limit(1) — eşzamanlı istek race'inde birden fazla aktif kod olsa 500 vermez
    result = await db.execute(
        select(VerificationCode).where(
            VerificationCode.user_id == uuid.UUID(user_id),
            VerificationCode.purpose == purpose,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > now,
        ).order_by(VerificationCode.expires_at.desc()).limit(1)
    )
    verification = result.scalar_one_or_none()

    if not verification:
        return False

    if target_email and verification.target_email != target_email:
        return False

    if verification.code != code:
        verification.failed_attempts += 1
        # 3 yanlış denemede kodu geçersiz kıl
        if verification.failed_attempts >= 3:
            verification.is_used = True
        await db.flush()
        return False

    verification.is_used = True
    await db.flush()
    return True


async def send_support_reply(user_email: str, subject: str, reply_text: str) -> bool:
    try:
        await asyncio.to_thread(resend.Emails.send, {
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
        await asyncio.to_thread(resend.Emails.send, {
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


async def send_contact_notification(contact) -> None:
    type_label = "İş Teklifi" if contact.type == "business" else "Genel İletişim"
    asyncio.create_task(_fire_resend({
        "from": "noreply@denikey.website",
        "to": "denisergocmen@gmail.com",
        "reply_to": contact.email,
        "subject": f"[DeniKey İletişim] {type_label} — {contact.subject}",
        "html": f"""
            <div style="font-family: sans-serif; max-width: 560px; margin: 0 auto;">
                <h2 style="color: #534AB7;">DeniKey — Yeni İletişim Formu</h2>
                <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
                    <tr><td style="padding:6px 0;color:#6b7280;width:100px">Tür</td><td><b>{type_label}</b></td></tr>
                    <tr><td style="padding:6px 0;color:#6b7280">Ad</td><td>{contact.name}</td></tr>
                    <tr><td style="padding:6px 0;color:#6b7280">E-posta</td><td><a href="mailto:{contact.email}">{contact.email}</a></td></tr>
                    <tr><td style="padding:6px 0;color:#6b7280">Konu</td><td>{contact.subject}</td></tr>
                </table>
                <div style="background:#f5f5f5;padding:16px;border-radius:8px;white-space:pre-wrap;font-size:14px;line-height:1.6">{contact.message}</div>
                <p style="color:#888;font-size:12px;margin-top:16px">Admin panelinden yönet: <a href="https://denikey-backend.fly.dev/admin">Admin Panel</a></p>
            </div>
        """,
    }))


async def send_email_change_notification(old_email: str) -> bool:
    try:
        await asyncio.to_thread(resend.Emails.send, {
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
