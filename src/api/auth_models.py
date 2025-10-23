"""
Pydantic models for authentication endpoints
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional


class RegisterRequest(BaseModel):
    """Request model for user registration"""
    email: EmailStr = Field(..., description="User's email address (must be unique)")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
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
        schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass123",
                "full_name": "John Doe"
            }
        }


class LoginRequest(BaseModel):
    """Request model for user login"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    
    @validator('email')
    def email_lowercase(cls, v):
        """Convert email to lowercase"""
        return v.lower().strip()
    
    class Config:
        schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass123"
            }
        }


class PasswordResetRequest(BaseModel):
    """Request model for initiating password reset"""
    email: EmailStr = Field(..., description="User's registered email address")
    
    @validator('email')
    def email_lowercase(cls, v):
        """Convert email to lowercase"""
        return v.lower().strip()
    
    class Config:
        schema_extra = {
            "example": {
                "email": "john.doe@example.com"
            }
        }


class VerifyResetRequest(BaseModel):
    """Request model for verifying OTP and resetting password"""
    email: EmailStr = Field(..., description="User's email address")
    otp: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$', description="6-digit OTP code")
    new_password: str = Field(..., min_length=6, description="New password (minimum 6 characters)")
    
    @validator('email')
    def email_lowercase(cls, v):
        """Convert email to lowercase"""
        return v.lower().strip()
    
    @validator('otp')
    def otp_digits_only(cls, v):
        """Validate OTP is 6 digits"""
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        if len(v) != 6:
            raise ValueError('OTP must be exactly 6 digits')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "otp": "123456",
                "new_password": "NewSecurePass123"
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
        schema_extra = {
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
        schema_extra = {
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


class PasswordResetResponse(BaseModel):
    """Response model for password reset request"""
    message: str = Field(..., description="Success message")
    email: str = Field(..., description="Email where OTP was sent")
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Password reset code sent to your email. Please check your inbox.",
                "email": "john.doe@example.com"
            }
        }


class PasswordResetCompleteResponse(BaseModel):
    """Response model for successful password reset"""
    message: str = Field(..., description="Success message")
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Password reset successful. You can now login with your new password."
            }
        }
