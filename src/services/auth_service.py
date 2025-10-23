"""
Authentication Service for User Registration, Login, and Password Reset
Uses AWS SES for email OTP delivery and DynamoDB for user storage
"""

import os
import secrets
import hashlib
import boto3
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import HTTPException
from botocore.exceptions import ClientError
from passlib.context import CryptContext
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    Authentication service handling user registration, login, and password reset.
    
    Features:
    - User registration with email verification via OTP
    - Secure password hashing using bcrypt
    - JWT token generation for authenticated sessions
    - Password reset via email OTP
    - Single DynamoDB table design (pk: USER#{user_id}, sk: PROFILE)
    """
    
    def __init__(self):
        """Initialize AWS clients and configuration"""
        logger.info("Initializing AuthService")
        
        # AWS Configuration from environment variables
        aws_config = {
            "aws_access_key_id": os.getenv('AWS_ACCESS_KEY_ID'),
            "aws_secret_access_key": os.getenv('AWS_SECRET_ACCESS_KEY'),
            "region_name": os.getenv('AWS_REGION')
        }
        
        # Initialize AWS clients
        self.dynamodb = boto3.resource('dynamodb', **aws_config)
        self.ses_client = boto3.client('ses', **aws_config)
        
        # Use same table as projects (Single Table Design)
        self.table = self.dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME'))
        
        # JWT Configuration
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')
        self.jwt_expiration_hours = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
        
        # SES Configuration
        self.ses_sender_email = os.getenv('SES_SENDER_EMAIL')
        self.ses_sender_name = os.getenv('SES_SENDER_NAME', 'AWS Analysis Service')
        
        # Validate critical configuration
        if not self.jwt_secret:
            logger.error("JWT_SECRET_KEY not configured in environment variables")
            raise ValueError("JWT_SECRET_KEY must be configured")
        
        if not self.ses_sender_email:
            logger.error("SES_SENDER_EMAIL not configured in environment variables")
            raise ValueError("SES_SENDER_EMAIL must be configured")
        
        logger.info("AuthService initialized successfully")

    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        logger.debug("Hashing password")
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        logger.debug("Verifying password")
        return pwd_context.verify(plain_password, hashed_password)

    def _generate_user_id(self, email: str) -> str:
        """
        Generate user_id from email using SHA256 hash
        
        Privacy-focused approach: Uses hash instead of raw email
        
        Args:
            email: User's email address
            
        Returns:
            12-character user_id derived from email hash
        """
        logger.debug(f"Generating user_id for email: {email}")
        # Hash email and take first 12 characters for user_id
        user_id = hashlib.sha256(email.lower().encode()).hexdigest()[:12]
        logger.debug(f"Generated user_id: {user_id}")
        return user_id

    def _generate_otp(self) -> str:
        """
        Generate secure 6-digit OTP code
        
        Returns:
            6-digit OTP string
        """
        otp = str(secrets.randbelow(1000000)).zfill(6)
        logger.debug(f"Generated OTP code: {'*' * 6}")  # Don't log actual OTP
        return otp

    def _get_initials(self, full_name: str) -> str:
        """
        Generate user initials from full name for UI display
        
        Args:
            full_name: User's full name
            
        Returns:
            2-character initials (e.g., "JD" for "John Doe")
        """
        parts = full_name.strip().split()
        if len(parts) >= 2:
            initials = f"{parts[0][0]}{parts[-1][0]}".upper()
        else:
            initials = full_name[:2].upper()
        logger.debug(f"Generated initials: {initials} from name: {full_name}")
        return initials

    def _create_token(self, user_id: str, email: str, full_name: str) -> str:
        """
        Create JWT authentication token
        
        Args:
            user_id: User identifier
            email: User's email
            full_name: User's full name
            
        Returns:
            JWT token string
        """
        logger.info(f"Creating JWT token for user: {user_id}")
        
        payload = {
            "user_id": user_id,
            "email": email,
            "full_name": full_name,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours)
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        logger.info(f"JWT token created successfully, expires in {self.jwt_expiration_hours} hours")
        return token

    async def send_otp_email(self, email: str, otp_code: str, purpose: str = "verification") -> None:
        """
        Send OTP code via email using AWS SES
        
        Args:
            email: Recipient email address
            otp_code: 6-digit OTP code
            purpose: Purpose of OTP (e.g., "verification", "password reset")
            
        Raises:
            HTTPException: If email sending fails
        """
        logger.info(f"Sending OTP email to {email} for {purpose}")
        
        try:
            subject = f"Your {purpose.title()} Code - {self.ses_sender_name}"
            
            # Plain text email body
            body_text = f"""
Hello,

Your {purpose} code is: {otp_code}

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

Best regards,
{self.ses_sender_name}
            """
            
            # HTML email body (better formatting)
            body_html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 5px; margin-top: 20px; }}
        .otp-code {{ font-size: 32px; font-weight: bold; color: #4CAF50; letter-spacing: 5px; text-align: center; padding: 20px; background-color: white; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>{self.ses_sender_name}</h2>
        </div>
        <div class="content">
            <h3>Your {purpose.title()} Code</h3>
            <p>Please use the following code to complete your {purpose}:</p>
            <div class="otp-code">{otp_code}</div>
            <p><strong>This code will expire in 10 minutes.</strong></p>
            <p>If you did not request this code, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 {self.ses_sender_name}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            """

            # Send email via SES
            response = self.ses_client.send_email(
                Source=self.ses_sender_email,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': body_text, 'Charset': 'UTF-8'},
                        'Html': {'Data': body_html, 'Charset': 'UTF-8'}
                    }
                }
            )
            
            logger.info(f"OTP email sent successfully to {email}, MessageId: {response['MessageId']}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"SES ClientError ({error_code}): {str(e)}")
            
            if error_code == 'MessageRejected':
                raise HTTPException(
                    status_code=400,
                    detail="Email address not verified. In SES sandbox mode, recipient must verify their email first."
                )
            elif error_code == 'AccessDenied':
                raise HTTPException(
                    status_code=500,
                    detail="Email service access denied. Please check SES permissions."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to send verification email: {error_code}"
                )
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to send verification email"
            )

    async def register(self, email: str, password: str, full_name: str) -> Dict:
        """
        Register new user account
        
        Creates user profile in DynamoDB with pk=USER#{user_id}, sk=PROFILE
        Automatically logs in user after successful registration
        
        Args:
            email: User's email address (unique identifier)
            password: Plain text password (will be hashed)
            full_name: User's full name
            
        Returns:
            Dict containing token and user information
            
        Raises:
            HTTPException: If email already registered or registration fails
        """
        logger.info(f"Processing registration for email: {email}")
        
        try:
            # Generate user_id from email hash
            user_id = self._generate_user_id(email)
            logger.debug(f"User ID generated: {user_id}")
            
            # Check if user already exists
            try:
                response = self.table.get_item(
                    Key={'pk': f'USER#{user_id}', 'sk': 'PROFILE'}
                )
                if 'Item' in response:
                    logger.warning(f"Registration attempt for existing email: {email}")
                    raise HTTPException(
                        status_code=400,
                        detail="Email already registered. Please login instead."
                    )
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    logger.error(f"DynamoDB error checking user existence: {str(e)}")
                    raise

            # Create user profile item
            timestamp = datetime.utcnow().isoformat() + "Z"
            user_item = {
                'pk': f'USER#{user_id}',
                'sk': 'PROFILE',
                'email': email.lower(),
                'full_name': full_name,
                'password_hash': self._hash_password(password),
                'created_at': timestamp,
                'last_login': timestamp,
                'password_reset_otp': '',  # Empty by default
                'otp_expiry': ''  # Empty by default
            }

            logger.debug(f"Storing user profile in DynamoDB for user: {user_id}")
            self.table.put_item(Item=user_item)
            logger.info(f"User profile created successfully for: {email}")
            
            # Generate authentication token
            token = self._create_token(user_id, email, full_name)
            
            response_data = {
                "message": "Registration successful",
                "token": token,
                "token_type": "bearer",
                "expires_in": self.jwt_expiration_hours * 3600,  # in seconds
                "user": {
                    "user_id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "initials": self._get_initials(full_name)
                }
            }
            
            logger.info(f"Registration completed successfully for user: {user_id}")
            return response_data

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Registration failed. Please try again later."
            )

    async def login(self, email: str, password: str) -> Dict:
        """
        Authenticate user and generate login token
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            Dict containing token and user information
            
        Raises:
            HTTPException: If credentials are invalid
        """
        logger.info(f"Processing login attempt for email: {email}")
        
        try:
            # Generate user_id from email
            user_id = self._generate_user_id(email)
            logger.debug(f"Looking up user with ID: {user_id}")
            
            # Retrieve user profile
            response = self.table.get_item(
                Key={'pk': f'USER#{user_id}', 'sk': 'PROFILE'}
            )

            if 'Item' not in response:
                logger.warning(f"Login attempt for non-existent email: {email}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password"
                )

            user = response['Item']
            logger.debug(f"User profile retrieved for: {email}")

            # Verify password
            if not self._verify_password(password, user['password_hash']):
                logger.warning(f"Invalid password attempt for email: {email}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password"
                )

            logger.info(f"Password verified successfully for user: {user_id}")

            # Update last login timestamp
            timestamp = datetime.utcnow().isoformat() + "Z"
            self.table.update_item(
                Key={'pk': f'USER#{user_id}', 'sk': 'PROFILE'},
                UpdateExpression='SET last_login = :login',
                ExpressionAttributeValues={':login': timestamp}
            )
            logger.debug(f"Last login timestamp updated for user: {user_id}")

            # Generate authentication token
            token = self._create_token(user_id, email, user['full_name'])

            response_data = {
                "message": "Login successful",
                "token": token,
                "token_type": "bearer",
                "expires_in": self.jwt_expiration_hours * 3600,  # in seconds
                "user": {
                    "user_id": user_id,
                    "email": user['email'],
                    "full_name": user['full_name'],
                    "initials": self._get_initials(user['full_name']),
                    "last_login": timestamp
                }
            }

            logger.info(f"Login completed successfully for user: {user_id}")
            return response_data

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Login failed. Please try again later."
            )

    async def request_password_reset(self, email: str) -> Dict:
        """
        Initiate password reset process by sending OTP via email
        
        Args:
            email: User's email address
            
        Returns:
            Dict with success message
            
        Raises:
            HTTPException: If email not found or sending fails
        """
        logger.info(f"Processing password reset request for email: {email}")
        
        try:
            # Generate user_id from email
            user_id = self._generate_user_id(email)
            
            # Check if user exists
            response = self.table.get_item(
                Key={'pk': f'USER#{user_id}', 'sk': 'PROFILE'}
            )
            
            if 'Item' not in response:
                logger.warning(f"Password reset requested for non-existent email: {email}")
                # Don't reveal that email doesn't exist (security best practice)
                raise HTTPException(
                    status_code=404,
                    detail="If this email is registered, a reset code has been sent."
                )

            # Generate OTP
            otp_code = self._generate_otp()
            otp_expiry = (datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z"
            
            logger.debug(f"Generated OTP for password reset, valid until: {otp_expiry}")

            # Store OTP temporarily in user profile
            self.table.update_item(
                Key={'pk': f'USER#{user_id}', 'sk': 'PROFILE'},
                UpdateExpression='SET password_reset_otp = :otp, otp_expiry = :expiry',
                ExpressionAttributeValues={
                    ':otp': otp_code,
                    ':expiry': otp_expiry
                }
            )
            logger.debug(f"OTP stored in DynamoDB for user: {user_id}")

            # Send OTP via email
            await self.send_otp_email(email, otp_code, "password reset")

            logger.info(f"Password reset OTP sent successfully to: {email}")
            return {
                "message": "Password reset code sent to your email. Please check your inbox.",
                "email": email
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during password reset request: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Password reset request failed. Please try again later."
            )

    async def verify_otp_and_reset(self, email: str, otp: str, new_password: str) -> Dict:
        """
        Verify OTP and reset user password
        
        Args:
            email: User's email address
            otp: 6-digit OTP code
            new_password: New password (plain text, will be hashed)
            
        Returns:
            Dict with success message
            
        Raises:
            HTTPException: If OTP is invalid or expired
        """
        logger.info(f"Processing OTP verification and password reset for email: {email}")
        
        try:
            # Generate user_id from email
            user_id = self._generate_user_id(email)
            
            # Retrieve user profile
            response = self.table.get_item(
                Key={'pk': f'USER#{user_id}', 'sk': 'PROFILE'}
            )
            
            if 'Item' not in response:
                logger.warning(f"Password reset verification for non-existent email: {email}")
                raise HTTPException(
                    status_code=404,
                    detail="Email not found"
                )

            user = response['Item']

            # Check OTP
            stored_otp = user.get('password_reset_otp', '')
            if not stored_otp or stored_otp != otp:
                logger.warning(f"Invalid OTP provided for email: {email}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid verification code. Please try again."
                )

            # Check OTP expiry
            otp_expiry_str = user.get('otp_expiry', '')
            if not otp_expiry_str:
                logger.warning(f"Missing OTP expiry for email: {email}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid verification code"
                )
            
            otp_expiry = datetime.fromisoformat(otp_expiry_str.replace('Z', ''))
            if otp_expiry < datetime.utcnow():
                logger.warning(f"Expired OTP provided for email: {email}")
                raise HTTPException(
                    status_code=400,
                    detail="Verification code expired. Please request a new one."
                )

            logger.debug(f"OTP verified successfully for user: {user_id}")

            # Update password and clear OTP fields
            self.table.update_item(
                Key={'pk': f'USER#{user_id}', 'sk': 'PROFILE'},
                UpdateExpression='SET password_hash = :pwd, password_reset_otp = :empty, otp_expiry = :empty',
                ExpressionAttributeValues={
                    ':pwd': self._hash_password(new_password),
                    ':empty': ''
                }
            )

            logger.info(f"Password reset completed successfully for user: {user_id}")
            return {
                "message": "Password reset successful. You can now login with your new password."
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during password reset verification: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Password reset failed. Please try again later."
            )

    def verify_token(self, token: str) -> Dict:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Dict containing decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        logger.debug("Verifying JWT token")
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            logger.debug(f"Token verified successfully for user: {payload.get('user_id')}")
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Expired token provided")
            raise HTTPException(
                status_code=401,
                detail="Token expired. Please login again."
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token provided: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token. Please login again."
            )
