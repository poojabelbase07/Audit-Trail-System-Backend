"""
User Schemas - Pydantic models for request/response validation
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.user import UserRole

class UserBase(BaseModel):
    """Base schema with common user fields"""
    email: EmailStr  # Validates email format automatically
    full_name: str  # User's display name

class UserCreate(UserBase):
    """Schema for user registration - requires password"""
    password: str  # Plaintext password (will be hashed before storage)
    
    @validator('password')
    def validate_password(cls, v):
        """Enforce password strength requirements"""
        if len(v) < 8:  # Minimum length check
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):  # Must contain number
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):  # Must contain uppercase
            raise ValueError('Password must contain at least one uppercase letter')
        return v  # Password valid
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Ensure name is not empty or just whitespace"""
        if not v or not v.strip():  # Check for empty/whitespace
            raise ValueError('Full name cannot be empty')
        if len(v.strip()) < 2:  # Minimum 2 characters
            raise ValueError('Full name must be at least 2 characters')
        return v.strip()  # Return trimmed name

class UserLogin(BaseModel):
    """Schema for login request"""
    email: EmailStr  # Validates email format
    password: str  # Plaintext password for verification

class UserResponse(UserBase):
    """Schema for user data in responses - excludes password"""
    id: UUID  # User unique identifier
    role: UserRole  # USER or ADMIN
    is_active: bool  # Account status
    created_at: datetime  # Registration timestamp
    last_login: Optional[datetime]  # Last successful login (None if never logged in)
    
    class Config:
        orm_mode = True  # Allow creation from SQLAlchemy models

class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = None  # Optional - only update if provided
    email: Optional[EmailStr] = None  # Optional - only update if provided
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Same validation as UserCreate"""
        if v is not None:  # Only validate if provided
            if not v or not v.strip():
                raise ValueError('Full name cannot be empty')
            if len(v.strip()) < 2:
                raise ValueError('Full name must be at least 2 characters')
            return v.strip()
        return v

class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    access_token: str  # JWT token
    token_type: str = "bearer"  # OAuth2 standard token type
    user: UserResponse  # Include user info in response