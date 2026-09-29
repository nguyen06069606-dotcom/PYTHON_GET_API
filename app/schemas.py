from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=256)
    roles: list[str] = Field(min_length=1)

class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    category: str
    price: Decimal
    discount_percentage: Decimal
    rating: Decimal
    stock: int
    brand: str | None
    sku: str
    thumbnail: str
    synced_at: datetime

class SyncResult(BaseModel):
    run_id: int
    status: str
    items_received: int
    items_inserted_or_updated: int

