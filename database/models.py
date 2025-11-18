from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    id: int
    telegram_id: int
    username: str
    full_name: str
    credit: int
    auth_token: Optional[str]
    playfab_id: Optional[str]
    created_at: datetime
    updated_at: datetime

@dataclass
class Product:
    id: int
    name: str
    credit_amount: int
    price: float
    is_active: bool
    created_at: datetime

@dataclass
class Transaction:
    id: int
    user_id: int
    product_id: int
    tx_id: str
    amount: float
    status: str
    proof_image_url: Optional[str]
    admin_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

@dataclass
class UserLivery:
    id: int
    user_id: int
    livery_id: str
    livery_name: str
    car_name: str
    injected_at: datetime

@dataclass
class Admin:
    id: int
    telegram_id: int
    username: str
    is_active: bool
    created_at: datetime