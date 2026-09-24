"""
Synapse RiskOps - Authentication Schemas
========================================
Owner: Person 2 | Week: 5

Pydantic models for authentication, tokens, and user profile responses.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credentials supplied to POST /api/auth/login."""

    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Plaintext password")


class TokenResponse(BaseModel):
    """JWT Bearer token returned upon successful login."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT payload data."""

    sub: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None


class UserResponse(BaseModel):
    """User profile returned by GET /api/auth/me."""

    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool