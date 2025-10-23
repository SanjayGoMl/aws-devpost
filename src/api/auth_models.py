"""
Pydantic models for authentication endpoints
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional


class RegisterRequest(BaseModel):
    """Request model for user registration"""
    email: EmailStr = Field(..., description="User's email address (must be unique)")
    password: str = Field(..., min_length=6, max_length=72, description="Password (6-72 characters)")
    full_name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    
    @validator('email')
    def email_lowercase(cls, v):
        """Convert email to lowercase"""
        return v.lower().strip()
    
    @validator('full_name')
    def name_not_empty(cls, v):
        """Validate name is not just whitespace"""
        if not v.strip():
            raise ValueError('Full name cannot be empty')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass123",
                "full_name": "John Doe"
            }
        }


class LoginRequest(BaseModel):
    """Request model for user login"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., max_length=72, description="User's password")
    
    @validator('email')
    def email_lowercase(cls, v):
        """Convert email to lowercase"""
        return v.lower().strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass123"
            }
        }


class UserProfile(BaseModel):
    """User profile information"""
    user_id: str = Field(..., description="Unique user identifier (hash of email)")
    email: str = Field(..., description="User's email address")
    full_name: str = Field(..., description="User's full name")
    initials: str = Field(..., description="User's initials for UI display (e.g., 'JD')")
    last_login: Optional[str] = Field(None, description="Last login timestamp (ISO format)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "3f4a8b9c2d1e",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "initials": "JD",
                "last_login": "2025-10-23T15:45:00Z"
            }
        }


class AuthResponse(BaseModel):
    """Response model for successful authentication (login/register)"""
    message: str = Field(..., description="Success message")
    token: str = Field(..., description="JWT authentication token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserProfile = Field(..., description="User profile information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Login successful",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "user_id": "3f4a8b9c2d1e",
                    "email": "john.doe@example.com",
                    "full_name": "John Doe",
                    "initials": "JD",
                    "last_login": "2025-10-23T15:45:00Z"
                }
            }
        }
