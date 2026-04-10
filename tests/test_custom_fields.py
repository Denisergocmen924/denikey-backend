"""
Custom fields veri yapısı ve serileştirme testleri.
Veritabanı gerektirmez — servis katmanının veri dönüşümlerini test eder.
"""
import pytest
from app.schemas.vault_item import (
    VaultItemCreate,
    VaultItemUpdate,
    CustomFieldCreate,
    CustomFieldData,
)


# ─── Schema Doğrulama ─────────────────────────────────────────────────────────

def test_vault_item_create_with_custom_fields_data():
    """custom_fields_data şifreli olmayan (ham) alan listesi kabul eder."""
    item = VaultItemCreate(
        encrypted_password="enc_pass",
        iv="some_iv",
        title="Gmail",
        custom_fields_data=[
            CustomFieldData(field_name="Kullanıcı Adı", value="user@gmail.com", field_type="text"),
            CustomFieldData(field_name="Yedek Kod", value="ABC123", field_type="secret"),
        ],
    )
    assert len(item.custom_fields_data) == 2
    assert item.custom_fields_data[0].field_name == "Kullanıcı Adı"
    assert item.custom_fields_data[1].field_type == "secret"


def test_vault_item_create_with_encrypted_custom_fields():
    """custom_fields şifreli alan listesi (encrypted_value) kabul eder."""
    item = VaultItemCreate(
        encrypted_password="enc_pass",
        custom_fields=[
            CustomFieldCreate(
                field_name="URL",
                field_type="text",
                encrypted_value="base64_encrypted",
                sort_order=0,
            ),
        ],
    )
    assert len(item.custom_fields) == 1
    assert item.custom_fields[0].encrypted_value == "base64_encrypted"


def test_vault_item_create_empty_custom_fields():
    """Custom field olmadan oluşturulabilir."""
    item = VaultItemCreate(encrypted_password="enc", custom_fields=[], custom_fields_data=[])
    assert item.custom_fields == []
    assert item.custom_fields_data == []


def test_vault_item_create_with_item_type_id():
    """item_type_id isteğe bağlı, UUID string kabul eder."""
    item = VaultItemCreate(
        encrypted_password="enc",
        item_type_id="550e8400-e29b-41d4-a716-446655440000",
        category_id="550e8400-e29b-41d4-a716-446655440001",
    )
    assert item.item_type_id == "550e8400-e29b-41d4-a716-446655440000"


def test_vault_item_update_custom_fields_data():
    """Güncelleme şeması custom_fields_data None kabul eder (değişmemiş)."""
    update = VaultItemUpdate(title="Yeni Başlık")
    assert update.custom_fields_data is None
    assert update.title == "Yeni Başlık"


def test_vault_item_update_clears_custom_fields():
    """Boş liste göndererek tüm custom fields silinebilir."""
    update = VaultItemUpdate(custom_fields_data=[])
    assert update.custom_fields_data == []


def test_custom_field_data_default_field_type():
    """field_type belirtilmezse 'text' varsayılan değerdir."""
    field = CustomFieldData(field_name="Alan", value="Değer")
    assert field.field_type == "text"


def test_custom_field_create_sort_order():
    """sort_order 0 varsayılan değerdir."""
    field = CustomFieldCreate(field_name="Alan", field_type="text")
    assert field.sort_order == 0


# ─── Serileştirme / Dönüşüm Testleri ─────────────────────────────────────────

def test_vault_item_create_model_dump():
    """model_dump() beklenmedik alanlar içermemeli."""
    item = VaultItemCreate(
        encrypted_password="enc",
        title="Test",
        custom_fields_data=[
            CustomFieldData(field_name="Alan", value="Değer"),
        ],
    )
    data = item.model_dump()
    assert "encrypted_password" in data
    assert "title" in data
    assert "custom_fields_data" in data
    # Şifrelenmemiş parola kesinlikle olmamalı
    assert "password" not in data


def test_vault_item_update_exclude_unset():
    """exclude_unset=True ile sadece değiştirilen alanlar döner."""
    update = VaultItemUpdate(title="Yeni")
    data = update.model_dump(exclude_unset=True)
    assert list(data.keys()) == ["title"]
    assert "encrypted_password" not in data
    assert "custom_fields_data" not in data
