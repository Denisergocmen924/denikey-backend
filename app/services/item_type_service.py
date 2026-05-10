from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.item_type import ItemType, ItemTypeField
import uuid

SYSTEM_ITEM_TYPES = [
    {
        "name_tr": "Giriş Bilgileri", "name_en": "Login",
        "icon": "lock", "color": "#534AB7", "sort_order": 0,
        "fields": [
            {"field_name_tr": "Kullanıcı Adı", "field_name_en": "Username", "field_type": "text", "is_required": False, "sort_order": 0},
            {"field_name_tr": "Şifre", "field_name_en": "Password", "field_type": "secret", "is_required": True, "sort_order": 1},
            {"field_name_tr": "URL", "field_name_en": "URL", "field_type": "text", "is_required": False, "sort_order": 2},
            {"field_name_tr": "Notlar", "field_name_en": "Notes", "field_type": "text", "is_required": False, "sort_order": 3},
        ]
    },
    {
        "name_tr": "Kredi/Banka Kartı", "name_en": "Card",
        "icon": "credit_card", "color": "#993C1D", "sort_order": 1,
        "fields": [
            {"field_name_tr": "Kart Adı", "field_name_en": "Card Name", "field_type": "text", "is_required": True, "sort_order": 0},
            {"field_name_tr": "Kart Numarası", "field_name_en": "Card Number", "field_type": "secret", "is_required": True, "sort_order": 1},
            {"field_name_tr": "Son Kullanma Tarihi", "field_name_en": "Expiry Date", "field_type": "text", "is_required": False, "sort_order": 2},
            {"field_name_tr": "CVV", "field_name_en": "CVV", "field_type": "secret", "is_required": False, "sort_order": 3},
            {"field_name_tr": "Kart Sahibi", "field_name_en": "Cardholder", "field_type": "text", "is_required": False, "sort_order": 4},
        ]
    },
    {
        "name_tr": "Kimlik", "name_en": "Identity",
        "icon": "badge", "color": "#185FA5", "sort_order": 2,
        "fields": [
            {"field_name_tr": "Ad Soyad", "field_name_en": "Full Name", "field_type": "text", "is_required": True, "sort_order": 0},
            {"field_name_tr": "TC Kimlik No", "field_name_en": "ID Number", "field_type": "secret", "is_required": True, "sort_order": 1},
            {"field_name_tr": "Doğum Tarihi", "field_name_en": "Birth Date", "field_type": "date", "is_required": False, "sort_order": 2},
            {"field_name_tr": "Seri No", "field_name_en": "Serial Number", "field_type": "text", "is_required": False, "sort_order": 3},
        ]
    },
    {
        "name_tr": "Güvenli Not", "name_en": "Secure Note",
        "icon": "note", "color": "#0F6E56", "sort_order": 3,
        "fields": [
            {"field_name_tr": "Not", "field_name_en": "Note", "field_type": "secret", "is_required": True, "sort_order": 0},
        ]
    },
    {
        "name_tr": "Wifi", "name_en": "Wifi",
        "icon": "wifi", "color": "#3B6D11", "sort_order": 4,
        "fields": [
            {"field_name_tr": "Ağ Adı", "field_name_en": "Network Name", "field_type": "text", "is_required": True, "sort_order": 0},
            {"field_name_tr": "Şifre", "field_name_en": "Password", "field_type": "secret", "is_required": True, "sort_order": 1},
            {"field_name_tr": "Güvenlik Tipi", "field_name_en": "Security Type", "field_type": "text", "is_required": False, "sort_order": 2},
        ]
    },
    {
        "name_tr": "IBAN/Banka Hesabı", "name_en": "Bank Account",
        "icon": "account_balance", "color": "#854F0B", "sort_order": 5,
        "fields": [
            {"field_name_tr": "Banka Adı", "field_name_en": "Bank Name", "field_type": "text", "is_required": True, "sort_order": 0},
            {"field_name_tr": "IBAN", "field_name_en": "IBAN", "field_type": "secret", "is_required": True, "sort_order": 1},
            {"field_name_tr": "Hesap Sahibi", "field_name_en": "Account Holder", "field_type": "text", "is_required": False, "sort_order": 2},
            {"field_name_tr": "Şube", "field_name_en": "Branch", "field_type": "text", "is_required": False, "sort_order": 3},
        ]
    },
    {
        "name_tr": "Üyelik/Abonelik", "name_en": "Membership",
        "icon": "subscriptions", "color": "#993556", "sort_order": 6,
        "fields": [
            {"field_name_tr": "Servis Adı", "field_name_en": "Service Name", "field_type": "text", "is_required": True, "sort_order": 0},
            {"field_name_tr": "Kullanıcı Adı", "field_name_en": "Username", "field_type": "text", "is_required": False, "sort_order": 1},
            {"field_name_tr": "Şifre", "field_name_en": "Password", "field_type": "secret", "is_required": True, "sort_order": 2},
            {"field_name_tr": "Yenileme Tarihi", "field_name_en": "Renewal Date", "field_type": "date", "is_required": False, "sort_order": 3},
            {"field_name_tr": "Ücret", "field_name_en": "Price", "field_type": "number", "is_required": False, "sort_order": 4},
        ]
    },
]


async def create_default_item_types(user_id: uuid.UUID, db: AsyncSession):
    for type_data in SYSTEM_ITEM_TYPES:
        item_type_id = uuid.uuid4()
        item_type = ItemType(
            id=item_type_id,
            user_id=user_id,
            name_tr=type_data["name_tr"],
            name_en=type_data["name_en"],
            icon=type_data["icon"],
            color=type_data["color"],
            is_system=False,
            sort_order=type_data["sort_order"],
        )
        db.add(item_type)

        for field_data in type_data["fields"]:
            field = ItemTypeField(
                id=uuid.uuid4(),
                item_type_id=item_type_id,
                field_name_tr=field_data["field_name_tr"],
                field_name_en=field_data["field_name_en"],
                field_type=field_data["field_type"],
                is_required=field_data["is_required"],
                sort_order=field_data["sort_order"],
            )
            db.add(field)

    await db.flush()


async def create_item_type(user_id: uuid.UUID, data: dict, db: AsyncSession) -> dict:
    item_type_id = uuid.uuid4()
    item_type = ItemType(
        id=item_type_id,
        user_id=user_id,
        name_tr=data["name_tr"],
        name_en=data.get("name_en", data["name_tr"]),
        icon=data.get("icon", "category"),
        color=data.get("color", "#534AB7"),
        is_system=False,
        sort_order=999,
    )
    db.add(item_type)

    # Kullanıcı alan tanımladıysa onları ekle; yoksa varsayılan "Şifre" alanı
    custom_fields = data.get("fields") or []
    if custom_fields:
        created_fields = []
        for i, f in enumerate(custom_fields):
            name = f["field_name"] if isinstance(f, dict) else f.field_name
            ftype = (f["field_type"] if isinstance(f, dict) else f.field_type) or "text"
            required = (f["is_required"] if isinstance(f, dict) else f.is_required) or False
            field_obj = ItemTypeField(
                id=uuid.uuid4(),
                item_type_id=item_type_id,
                field_name_tr=name,
                field_name_en=name,
                field_type=ftype,
                is_required=required,
                sort_order=i,
            )
            db.add(field_obj)
            created_fields.append(field_obj)
    else:
        default = ItemTypeField(
            id=uuid.uuid4(),
            item_type_id=item_type_id,
            field_name_tr="Şifre",
            field_name_en="Password",
            field_type="secret",
            is_required=True,
            sort_order=0,
        )
        db.add(default)
        created_fields = [default]

    await db.flush()
    await db.refresh(item_type)
    return {
        "id": str(item_type.id),
        "name_tr": item_type.name_tr,
        "name_en": item_type.name_en,
        "icon": item_type.icon,
        "color": item_type.color,
        "is_system": item_type.is_system,
        "sort_order": item_type.sort_order,
        "fields": [
            {
                "id": str(f.id),
                "field_name_tr": f.field_name_tr,
                "field_name_en": f.field_name_en,
                "field_type": f.field_type,
                "is_required": f.is_required,
                "sort_order": f.sort_order,
            }
            for f in created_fields
        ],
    }


async def update_item_type(user_id: uuid.UUID, item_type_id: str, data: dict, db: AsyncSession) -> dict:
    from fastapi import HTTPException
    result = await db.execute(
        select(ItemType)
        .options(selectinload(ItemType.fields))
        .where(ItemType.id == uuid.UUID(item_type_id), ItemType.user_id == user_id)
    )
    item_type = result.scalar_one_or_none()
    if not item_type:
        raise HTTPException(status_code=404, detail="Tür bulunamadı")
    if item_type.is_system:
        raise HTTPException(status_code=403, detail="Sistem türleri düzenlenemez")
    if "name_tr" in data:
        item_type.name_tr = data["name_tr"]
        item_type.name_en = data.get("name_en", data["name_tr"])
    if "icon" in data:
        item_type.icon = data["icon"]
    if "color" in data:
        item_type.color = data["color"]
    if data.get("fields"):
        field_map = {str(f.id): f for f in item_type.fields}
        for field_update in data["fields"]:
            fid = field_update["id"]
            fname = field_update["field_name"].strip()
            if fid in field_map and fname:
                field_map[fid].field_name_tr = fname
                field_map[fid].field_name_en = fname
    await db.flush()
    await db.refresh(item_type)
    return {
        "id": str(item_type.id),
        "name_tr": item_type.name_tr,
        "name_en": item_type.name_en,
        "icon": item_type.icon,
        "color": item_type.color,
        "is_system": item_type.is_system,
        "sort_order": item_type.sort_order,
        "fields": [
            {
                "id": str(f.id),
                "field_name_tr": f.field_name_tr,
                "field_name_en": f.field_name_en,
                "field_type": f.field_type,
                "is_required": f.is_required,
                "sort_order": f.sort_order,
            }
            for f in sorted(item_type.fields, key=lambda x: x.sort_order)
        ],
    }


async def delete_item_type(user_id: uuid.UUID, item_type_id: str, db: AsyncSession):
    from fastapi import HTTPException
    from fastapi import status as http_status
    result = await db.execute(
        select(ItemType).where(
            ItemType.id == uuid.UUID(item_type_id),
            ItemType.user_id == user_id,
        )
    )
    item_type = result.scalar_one_or_none()
    if not item_type:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Tür bulunamadı")
    if item_type.is_system:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Sistem türleri silinemez")
    await db.delete(item_type)
    await db.flush()


async def get_item_types(user_id: uuid.UUID, db: AsyncSession) -> list:
    result = await db.execute(
        select(ItemType)
        .options(selectinload(ItemType.fields))
        .where(ItemType.user_id == user_id)
        .order_by(ItemType.sort_order)
    )
    item_types = result.scalars().all()
    return [
        {
            "id": str(it.id),
            "name_tr": it.name_tr,
            "name_en": it.name_en,
            "icon": it.icon,
            "color": it.color,
            "is_system": it.is_system,
            "sort_order": it.sort_order,
            "fields": [
                {
                    "id": str(f.id),
                    "field_name_tr": f.field_name_tr,
                    "field_name_en": f.field_name_en,
                    "field_type": f.field_type,
                    "is_required": f.is_required,
                    "sort_order": f.sort_order,
                }
                for f in sorted(it.fields, key=lambda x: x.sort_order)
            ]
        }
        for it in item_types
    ]
