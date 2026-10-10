"""
Shared Pydantic Schemas for Live E-Commerce Microservices.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Auth & User Schemas
# -------------------------------------------------------------
class UserRegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    address: Optional[str] = "221B Baker St, London"


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserProfile(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: str
    address: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


# -------------------------------------------------------------
# Catalog & Inventory Schemas
# -------------------------------------------------------------
class Product(BaseModel):
    id: str
    name: str
    category: str
    price: float
    description: str
    image_url: str
    rating: float = 4.8
    stock_count: int = 50


class InventoryCheckRequest(BaseModel):
    product_id: str
    quantity: int = 1


class InventoryReserveRequest(BaseModel):
    order_id: str
    items: List[Dict[str, Any]]


# -------------------------------------------------------------
# Cart Schemas
# -------------------------------------------------------------
class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int
    image_url: str


class CartState(BaseModel):
    user_id: str
    items: List[CartItem] = []
    total_amount: float = 0.0


# -------------------------------------------------------------
# Order & Payment Schemas
# -------------------------------------------------------------
class CheckoutRequest(BaseModel):
    user_id: str
    payment_method: str = "credit_card"  # credit_card, upi, netbanking
    shipping_address: str = "221B Baker St, London"


class PaymentProcessRequest(BaseModel):
    order_id: str
    user_id: str
    amount: float
    payment_method: str


class PaymentReceipt(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    status: str  # SUCCESS, FAILED
    transaction_ref: str
    processed_at: str


class Order(BaseModel):
    order_id: str
    user_id: str
    items: List[CartItem]
    total_amount: float
    status: str  # PENDING, INVENTORY_RESERVED, PAID, CONFIRMED, FAILED
    payment_id: Optional[str] = None
    created_at: str
    shipping_address: str


# -------------------------------------------------------------
# Notification Schemas
# -------------------------------------------------------------
class NotificationEvent(BaseModel):
    id: str
    user_id: str
    type: str  # ORDER_CONFIRMED, PAYMENT_SUCCESS, INVENTORY_ALERT
    title: str
    message: str
    timestamp: str
    read: bool = False
