# Authentication System Documentation

## Overview

This document describes the authentication system implementation for the AWS Image and Excel Analysis Service. The system provides user registration, login, and password reset functionality using AWS services.

## Architecture

### Single Table Design

The authentication system uses the **same DynamoDB table** as the project storage to maintain a unified data model:

```
Table: DYNAMODB_TABLE_NAME (from environment)

User Profile Items:
- pk: "USER#{user_id}"
- sk: "PROFILE"
- email: "user@example.com"
- full_name: "John Doe"
- password_hash: "bcrypt_hashed_password"
- created_at: "2025-10-23T10:30:00Z"
- last_login: "2025-10-23T15:45:00Z"
- password_reset_otp: "" (temporary during password reset)
- otp_expiry: "" (temporary OTP expiration timestamp)

Project Items (existing):
- pk: "USER#{user_id}"
- sk: "PROJECT#{folder_name}"
- ... (project data)
```

### User ID Generation

User IDs are generated using SHA256 hash of the email address:

```python
import hashlib
user_id = hashlib.sha256(email.lower().encode()).hexdigest()[:12]
# Example: "3f4a8b9c2d1e"
```

**Benefits:**
- Privacy-focused (email not exposed in URLs)
- Deterministic (same email always generates same user_id)
- Short and URL-safe (12 characters)
- No collisions in practice

## Authentication Flow

### 1. User Registration

**Endpoint:** `POST /api/auth/register`

**Request:**
```json
{
  "email": "john@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe"
}
```

**Process:**
1. Email is converted to lowercase and validated
2. User ID is generated from email hash
3. Check if user already exists in DynamoDB
4. Password is hashed using bcrypt
5. User profile is stored in DynamoDB with pk=`USER#{user_id}`, sk=`PROFILE`
6. JWT token is generated and returned
7. User is automatically logged in

**Response:**
```json
{
  "message": "Registration successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "user_id": "3f4a8b9c2d1e",
    "email": "john@example.com",
    "full_name": "John Doe",
    "initials": "JD",
    "last_login": "2025-10-23T15:45:00Z"
  }
}
```

**Logging:**
- Registration request received
- User ID generation
- DynamoDB write operation
- Token generation
- Success/failure

### 2. User Login

**Endpoint:** `POST /api/auth/login`

**Request:**
```json
{
  "email": "john@example.com",
  "password": "SecurePass123"
}
```

**Process:**
1. Generate user_id from email
2. Retrieve user profile from DynamoDB
3. Verify password using bcrypt
4. Update last_login timestamp
5. Generate JWT token
6. Return token and user profile

**Response:**
```json
{
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "user_id": "3f4a8b9c2d1e",
    "email": "john@example.com",
    "full_name": "John Doe",
    "initials": "JD",
    "last_login": "2025-10-23T16:30:00Z"
  }
}
```

**Logging:**
- Login attempt received
- User lookup in DynamoDB
- Password verification (success/failure)
- Last login timestamp update
- Token generation

### 3. Password Reset (2-Step Process)

#### Step 1: Request Password Reset

**Endpoint:** `POST /api/auth/request-password-reset`

**Request:**
```json
{
  "email": "john@example.com"
}
```

**Process:**
1. Generate user_id from email
2. Check if user exists in DynamoDB
3. Generate 6-digit OTP code
4. Set OTP expiry (10 minutes from now)
5. Store OTP in user profile (temporary fields)
6. Send OTP via AWS SES email
7. Return success message

**Response:**
```json
{
  "message": "Password reset code sent to your email. Please check your inbox.",
  "email": "john@example.com"
}
```

**Email Template:**
```
Subject: Your Password Reset Code - AWS Analysis Service

Your password reset code is: 123456

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.
```

**Logging:**
- Password reset requested
- OTP generation
- DynamoDB update (OTP storage)
- SES email sent
- Message ID from SES

#### Step 2: Verify OTP and Reset Password

**Endpoint:** `POST /api/auth/verify-reset`

**Request:**
```json
{
  "email": "john@example.com",
  "otp": "123456",
  "new_password": "NewSecurePass456"
}
```

**Process:**
1. Generate user_id from email
2. Retrieve user profile from DynamoDB
3. Validate OTP matches stored value
4. Check OTP hasn't expired (< 10 minutes old)
5. Hash new password with bcrypt
6. Update password_hash in DynamoDB
7. Clear OTP fields (password_reset_otp, otp_expiry)
8. Return success message

**Response:**
```json
{
  "message": "Password reset successful. You can now login with your new password."
}
```

**Logging:**
- OTP verification requested
- OTP validation (match/mismatch)
- Expiry check (valid/expired)
- Password update in DynamoDB
- OTP cleared

## Security Features

### Password Security

1. **Bcrypt Hashing:**
   - Passwords are never stored in plain text
   - Uses bcrypt with automatic salt generation
   - Computationally expensive to prevent brute force

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed = pwd_context.hash(password)
```

2. **Password Requirements:**
   - Minimum 6 characters (configurable)
   - Can be enhanced with complexity rules

### JWT Token Security

1. **Token Structure:**
```json
{
  "user_id": "3f4a8b9c2d1e",
  "email": "john@example.com",
  "full_name": "John Doe",
  "iat": 1698765432,
  "exp": 1698851832
}
```

2. **Token Configuration:**
   - Secret key from environment (JWT_SECRET_KEY)
   - Algorithm: HS256
   - Expiration: 24 hours (configurable via JWT_EXPIRATION_HOURS)

3. **Token Usage:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### OTP Security

1. **Generation:**
   - Uses `secrets.randbelow()` for cryptographically secure random numbers
   - 6-digit code (000000-999999)

2. **Expiration:**
   - Valid for 10 minutes only
   - Stored with ISO timestamp in DynamoDB

3. **Single Use:**
   - OTP is cleared after successful password reset
   - Cannot be reused

### Email Security (AWS SES)

1. **Sender Verification:**
   - Sender email must be verified in AWS SES
   - Prevents email spoofing

2. **Sandbox Mode (for testing):**
   - Recipient emails must also be verified
   - Limited to 200 emails/day

3. **Production Mode:**
   - Can send to any email address
   - Higher sending limits

## Environment Variables

Required configuration in `.env` file:

```bash
# Existing AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=your_table_name

# Authentication Configuration
JWT_SECRET_KEY=generate-random-secret-key-minimum-32-characters
JWT_EXPIRATION_HOURS=24

# AWS SES Configuration
SES_SENDER_EMAIL=noreply@yourdomain.com
SES_SENDER_NAME=AWS Analysis Service
```

### Generating JWT Secret Key

```bash
# Generate secure random secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## AWS Configuration Required

### 1. DynamoDB Table

No additional table needed - uses existing project table with different sort key:

```bash
# Table already exists with:
# - pk: String (partition key)
# - sk: String (sort key)
# - Billing mode: On-demand

# New items added:
# USER#{user_id}#PROFILE - User profiles
# USER#{user_id}#PROJECT#{folder_name} - Projects (existing)
```

### 2. AWS SES Setup

#### Enable SES:
```bash
1. Go to AWS Console → Amazon SES
2. Select your region (must match AWS_REGION)
3. Verify sender email address
```

#### Verify Sender Email:
```bash
1. SES Console → Verified Identities → Create Identity
2. Select "Email Address"
3. Enter sender email (e.g., noreply@yourdomain.com)
4. Check inbox and click verification link
```

#### For Testing (Sandbox Mode):
```bash
1. Verify test recipient emails
2. SES Console → Verified Identities → Create Identity
3. Each test user must verify their email
4. Limited to 200 emails/day
```

#### For Production:
```bash
1. SES Console → Account Dashboard
2. Click "Request production access"
3. Fill out use case form
4. AWS typically approves within 24 hours
5. Can then send to any email address
```

### 3. IAM Permissions

Add to your IAM user/role policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/TABLE_NAME"
    }
  ]
}
```

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | Login user | No |
| POST | `/api/auth/request-password-reset` | Request password reset OTP | No |
| POST | `/api/auth/verify-reset` | Verify OTP and reset password | No |

### Protected Endpoints (Future)

To protect an endpoint with JWT authentication:

```python
from fastapi import Depends

@router.get("/protected-route")
async def protected_route(token_data: dict = Depends(verify_token)):
    user_id = token_data['user_id']
    email = token_data['email']
    # Your protected logic here
    return {"message": f"Hello {email}"}
```

## Error Handling

### Common Error Responses

1. **Email Already Registered (400):**
```json
{
  "detail": "Email already registered. Please login instead."
}
```

2. **Invalid Credentials (401):**
```json
{
  "detail": "Invalid email or password"
}
```

3. **Invalid/Expired Token (401):**
```json
{
  "detail": "Token expired. Please login again."
}
```

4. **Invalid OTP (400):**
```json
{
  "detail": "Invalid verification code. Please try again."
}
```

5. **Expired OTP (400):**
```json
{
  "detail": "Verification code expired. Please request a new one."
}
```

6. **SES Email Error (400/500):**
```json
{
  "detail": "Email address not verified. In SES sandbox mode, recipient must verify their email first."
}
```

## Logging

All authentication operations are logged with appropriate log levels:

### Log Levels

- **INFO:** Successful operations, important state changes
- **WARNING:** Failed attempts, invalid inputs
- **ERROR:** System errors, AWS service failures
- **DEBUG:** Detailed operation flow (not in production)

### Example Log Entries

```
2025-10-23 15:45:12 - auth_service - INFO - Initializing AuthService
2025-10-23 15:45:30 - auth_service - INFO - Processing registration for email: john@example.com
2025-10-23 15:45:31 - auth_service - DEBUG - User ID generated: 3f4a8b9c2d1e
2025-10-23 15:45:31 - auth_service - INFO - User profile created successfully for: john@example.com
2025-10-23 15:45:31 - auth_service - INFO - JWT token created successfully, expires in 24 hours
2025-10-23 15:45:31 - routes - INFO - Registration successful for email: john@example.com
```

### Sensitive Data Protection

- Passwords are **never** logged
- OTP codes are masked in logs (`'*' * 6`)
- Email addresses are logged for audit trail
- Tokens are not logged in full

## Testing

### 1. Register a New User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123",
    "full_name": "Test User"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'
```

### 3. Request Password Reset

```bash
curl -X POST http://localhost:8000/api/auth/request-password-reset \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }'
```

### 4. Reset Password with OTP

```bash
curl -X POST http://localhost:8000/api/auth/verify-reset \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "otp": "123456",
    "new_password": "NewTestPass456"
  }'
```

### 5. Use Token in Authenticated Request

```bash
curl -X GET http://localhost:8000/api/projects/3f4a8b9c2d1e \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Frontend Integration

### User Registration Flow

```javascript
async function register(email, password, fullName) {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: email,
      password: password,
      full_name: fullName
    })
  });
  
  const data = await response.json();
  
  if (response.ok) {
    // Store token in localStorage or sessionStorage
    localStorage.setItem('auth_token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    
    // Display user initials in UI
    document.getElementById('user-avatar').textContent = data.user.initials;
    
    return data;
  } else {
    throw new Error(data.detail);
  }
}
```

### User Login Flow

```javascript
async function login(email, password) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  const data = await response.json();
  
  if (response.ok) {
    localStorage.setItem('auth_token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    return data;
  } else {
    throw new Error(data.detail);
  }
}
```

### Password Reset Flow

```javascript
// Step 1: Request OTP
async function requestPasswordReset(email) {
  const response = await fetch('/api/auth/request-password-reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  
  const data = await response.json();
  
  if (response.ok) {
    alert('Check your email for the verification code');
    return data;
  } else {
    throw new Error(data.detail);
  }
}

// Step 2: Verify OTP and reset
async function resetPassword(email, otp, newPassword) {
  const response = await fetch('/api/auth/verify-reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: email,
      otp: otp,
      new_password: newPassword
    })
  });
  
  const data = await response.json();
  
  if (response.ok) {
    alert('Password reset successful! Please login.');
    return data;
  } else {
    throw new Error(data.detail);
  }
}
```

### Using Token in Requests

```javascript
async function makeAuthenticatedRequest(url) {
  const token = localStorage.getItem('auth_token');
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (response.status === 401) {
    // Token expired, redirect to login
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  }
  
  return response.json();
}
```

### Displaying User Avatar

```html
<!-- Circular avatar with initials -->
<div class="user-avatar" id="user-avatar">JD</div>

<style>
.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #4CAF50;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
}
</style>

<script>
// Set initials from stored user data
const user = JSON.parse(localStorage.getItem('user'));
if (user) {
  document.getElementById('user-avatar').textContent = user.initials;
}
</script>
```

## Deployment Checklist

- [ ] Generate strong JWT_SECRET_KEY (32+ characters)
- [ ] Configure JWT_EXPIRATION_HOURS (default: 24)
- [ ] Verify sender email in AWS SES
- [ ] Add SES permissions to IAM role/user
- [ ] Update SES_SENDER_EMAIL in production .env
- [ ] Request SES production access (if needed)
- [ ] Test email delivery in sandbox mode
- [ ] Verify DynamoDB table exists and is accessible
- [ ] Install new dependencies: `pip install PyJWT passlib[bcrypt]`
- [ ] Test all authentication endpoints
- [ ] Set up monitoring for failed login attempts
- [ ] Configure CORS for frontend domain
- [ ] Enable HTTPS in production
- [ ] Set up log aggregation for security auditing

## Troubleshooting

### Email Not Received

1. **Check SES Sandbox Mode:**
   - Recipient email must be verified in SES console
   - Or request production access

2. **Check Spam Folder:**
   - OTP emails might be flagged as spam

3. **Check SES Sending Limits:**
   - Sandbox: 200 emails/day
   - Check AWS SES console for quota

4. **Check SES Logs:**
   - CloudWatch Logs for SES delivery status

### Token Errors

1. **Token Expired:**
   - User needs to login again
   - Consider implementing refresh tokens

2. **Invalid Token:**
   - Check JWT_SECRET_KEY matches between restarts
   - Token might be corrupted in storage

3. **Missing Authorization Header:**
   - Ensure frontend sends: `Authorization: Bearer <token>`

### DynamoDB Errors

1. **ResourceNotFoundException:**
   - Table doesn't exist or wrong name in .env
   - Check DYNAMODB_TABLE_NAME

2. **AccessDenied:**
   - IAM permissions insufficient
   - Add DynamoDB GetItem/PutItem/UpdateItem permissions

## Future Enhancements

1. **Email Verification:**
   - Send OTP during registration
   - Mark account as verified

2. **Refresh Tokens:**
   - Long-lived refresh tokens
   - Short-lived access tokens

3. **Rate Limiting:**
   - Limit login attempts
   - Prevent brute force attacks

4. **2FA (Two-Factor Authentication):**
   - TOTP-based 2FA
   - SMS-based 2FA

5. **Social Login:**
   - Google OAuth
   - GitHub OAuth

6. **Password Complexity:**
   - Enforce strong passwords
   - Check against common passwords

7. **Account Management:**
   - Update profile
   - Delete account
   - Change email

8. **Audit Logging:**
   - Track all authentication events
   - Store in separate audit table

## Support

For issues or questions:
1. Check CloudWatch Logs for detailed error messages
2. Verify all environment variables are set correctly
3. Test AWS services (SES, DynamoDB) independently
4. Review this documentation for configuration steps
