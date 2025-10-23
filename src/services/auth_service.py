"""
Authentication Service for User Registration and Login
Minimal POC version - Uses DynamoDB for user storage
"""

import os
import hashlib
import boto3
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict
from fastapi import HTTPException
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service handling user registration and login.
    
    Features:
    - User registration with email and password
    - Secure password hashing using bcrypt
    - JWT token generation for authenticated sessions
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
        
        # Use same table as projects (Single Table Design)
        self.table = self.dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME'))
        
        # JWT Configuration
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')
        self.jwt_expiration_hours = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
        
        # Validate critical configuration
        if not self.jwt_secret:
            logger.error("JWT_SECRET_KEY not configured in environment variables")
            raise ValueError("JWT_SECRET_KEY must be configured")
        
        logger.info("AuthService initialized successfully")

    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt
        
        Args:
            password: Plain text password (max 72 bytes due to bcrypt limitation)
            
        Returns:
            Hashed password string
            
        Raises:
            ValueError: If password hashing fails
        """
        logger.debug("Hashing password")
        
        try:
            # Convert password to bytes and hash with bcrypt
            password_bytes = password.encode('utf-8')
            # Generate salt and hash
            hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
            # Return as string for storage
            logger.debug("Password hashed successfully")
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Bcrypt hashing error: {str(e)}")
            raise ValueError(f"Password hashing failed: {str(e)}")

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
        try:
            # Convert both to bytes for bcrypt comparison
            password_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False

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

            # Hash password before creating user item
            try:
                password_hash = self._hash_password(password)
            except ValueError as e:
                logger.error(f"Password hashing failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Password hashing failed. Please try again."
                )
            
            # Create user profile item
            timestamp = datetime.utcnow().isoformat() + "Z"
            user_item = {
                'pk': f'USER#{user_id}',
                'sk': 'PROFILE',
                'email': email.lower(),
                'full_name': full_name,
                'password_hash': password_hash,
                'created_at': timestamp,
                'last_login': timestamp
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
