# Authentication System Setup Guide

## Quick Start

This guide will help you set up the authentication system for the AWS Image and Excel Analysis Service.

## Prerequisites

- Python 3.8+
- AWS Account with access to:
  - DynamoDB
  - S3
  - SES (Simple Email Service)
  - Bedrock
- Existing project configured and running

## Installation Steps

### 1. Install New Dependencies

```bash
cd /Users/sanjays/Docments/AWS_Frontend/AWS_October

# Install new authentication dependencies
pip install PyJWT==2.8.0 passlib[bcrypt]==1.7.4

# Or install all requirements
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Update your `.env` file with authentication configuration:

```bash
# Copy example if you don't have .env yet
cp .env.example .env

# Edit .env and add these new variables:
```

Add to your `.env`:

```bash
# Authentication Configuration
JWT_SECRET_KEY=YOUR_RANDOM_SECRET_KEY_HERE
JWT_EXPIRATION_HOURS=24

# AWS SES Configuration
SES_SENDER_EMAIL=noreply@yourdomain.com
SES_SENDER_NAME=AWS Analysis Service
```

**Generate JWT Secret Key:**

```bash
# Run this command to generate a secure secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Copy the output and paste it as JWT_SECRET_KEY in .env
```

Example output:
```
dK7xP9zR2qW5vY8nM4jL6sG1hT3fC0bN9mX7kV2eQ8pU4wA
```

### 3. Configure AWS SES (Email Service)

#### Step 3a: Verify Sender Email

1. **Go to AWS SES Console:**
   ```
   https://console.aws.amazon.com/ses/
   ```

2. **Select Your Region:**
   - Must match your `AWS_REGION` in .env
   - Example: `us-east-1`

3. **Create Verified Identity:**
   - Click "Verified Identities" → "Create Identity"
   - Select "Email Address"
   - Enter your sender email (e.g., `noreply@yourdomain.com`)
   - Click "Create Identity"

4. **Verify Email:**
   - Check the inbox of your sender email
   - Click the verification link from AWS
   - Status should change to "Verified"

5. **Update .env:**
   ```bash
   SES_SENDER_EMAIL=noreply@yourdomain.com
   ```

#### Step 3b: Sandbox Mode (For Testing)

AWS SES starts in "Sandbox Mode" which has limitations:
- Can only send to verified email addresses
- Limited to 200 emails per day
- 1 email per second rate limit

**To Test in Sandbox Mode:**

1. **Verify Test User Emails:**
   - Go to SES Console → Verified Identities
   - Click "Create Identity" → Email Address
   - Enter each test user's email
   - They must click verification link

2. **Test the System:**
   - Register with verified email
   - Request password reset
   - Receive OTP in email

#### Step 3c: Production Access (Optional)

For production use, request production access:

1. **Go to SES Console:**
   - Click "Account Dashboard"
   - Click "Request production access"

2. **Fill Out Form:**
   - Mail type: Transactional
   - Website URL: Your website/app URL
   - Use case: "User authentication and password reset OTPs"
   - Compliance: Describe how users opt-in

3. **Wait for Approval:**
   - Usually approved within 24 hours
   - Once approved, can send to any email
   - Higher sending limits

### 4. Update IAM Permissions

Add SES permissions to your AWS IAM user/role:

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
    }
  ]
}
```

**How to Add:**

1. Go to AWS IAM Console
2. Find your user/role (the one used by your app)
3. Click "Add permissions" → "Create inline policy"
4. Click JSON tab
5. Paste the above policy
6. Name it: `SESEmailSendPolicy`
7. Click "Create policy"

### 5. Verify DynamoDB Table

No new table needed! The authentication system uses your existing project table.

**Verify Table Configuration:**

```bash
# Check if table exists
aws dynamodb describe-table --table-name YOUR_TABLE_NAME

# Should have:
# - Partition Key (pk): String
# - Sort Key (sk): String
# - Billing mode: On-demand or Provisioned
```

The authentication adds new items with:
- `pk`: `USER#{user_id}`
- `sk`: `PROFILE`

Projects continue using:
- `pk`: `USER#{user_id}`
- `sk`: `PROJECT#{folder_name}`

### 6. Test the Installation

Run the test script to verify everything is working:

```bash
# Make test script executable
chmod +x test_auth_apis.py

# Run authentication tests
python3 test_auth_apis.py
```

**Expected Output:**
```
🚀 AWS Analysis Service - Authentication System Tests
======================================================================
TEST 0: Health Check
✅ API is healthy!

TEST 1: User Registration
✅ Registration successful!
   User ID: 3f4a8b9c2d1e
   Email: test_20251023151234@example.com
   ...

TEST 2: User Login
✅ Login successful!
   ...

📊 Test Results Summary
Total Tests: 6
Passed: 6
Failed: 0
Success Rate: 100.0%

🎉 All tests passed! Authentication system is working correctly.
```

## File Structure

New files added:

```
AWS_October/
├── src/
│   ├── services/
│   │   ├── auth_service.py          # NEW: Authentication service
│   │   └── aws_service.py           # Existing
│   └── api/
│       ├── auth_models.py           # NEW: Auth Pydantic models
│       ├── routes.py                # UPDATED: Added auth endpoints
│       └── models.py                # Existing
├── test_auth_apis.py                # NEW: Auth testing script
├── AUTHENTICATION_DOCUMENTATION.md  # NEW: Detailed docs
├── AUTHENTICATION_SETUP.md          # NEW: This file
├── requirements.txt                 # UPDATED: Added PyJWT, passlib
└── .env.example                     # UPDATED: Added auth config
```

## Configuration Summary

### Required Environment Variables

```bash
# Existing AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_bucket
DYNAMODB_TABLE_NAME=your_table

# NEW: Authentication
JWT_SECRET_KEY=your-generated-secret-key-32-chars-minimum
JWT_EXPIRATION_HOURS=24

# NEW: Email Service
SES_SENDER_EMAIL=noreply@yourdomain.com
SES_SENDER_NAME=AWS Analysis Service
```

### AWS Services Used

| Service | Purpose | Configuration Required |
|---------|---------|----------------------|
| DynamoDB | User storage & projects | Existing table (no changes) |
| SES | Send OTP emails | Verify sender email |
| IAM | Permissions | Add SES send permissions |

## API Endpoints Added

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login user |
| `/api/auth/request-password-reset` | POST | Request OTP for password reset |
| `/api/auth/verify-reset` | POST | Verify OTP and reset password |

### Example API Calls

**Register:**
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "full_name": "John Doe"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

## Troubleshooting

### Issue: "JWT_SECRET_KEY must be configured"

**Solution:**
```bash
# Generate secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
JWT_SECRET_KEY=the-generated-key-here
```

### Issue: "SES_SENDER_EMAIL must be configured"

**Solution:**
```bash
# Add to .env
SES_SENDER_EMAIL=noreply@yourdomain.com

# Verify email in AWS SES Console
```

### Issue: "Email address not verified"

**Solution:**
- Go to AWS SES Console
- Verify sender email (noreply@yourdomain.com)
- If in sandbox, verify recipient emails too
- Click verification links in email

### Issue: "Failed to send verification email"

**Solutions:**
1. **Check IAM Permissions:**
   ```bash
   # Ensure your IAM user/role has:
   - ses:SendEmail
   - ses:SendRawEmail
   ```

2. **Check SES Region:**
   ```bash
   # AWS_REGION in .env must match SES setup region
   AWS_REGION=us-east-1
   ```

3. **Check SES Console:**
   - Go to SES → Account Dashboard
   - Check sending statistics
   - Look for bounces/complaints

### Issue: "Email already registered"

**Solution:**
- This is expected behavior (working correctly)
- Use a different email
- Or login with existing email

### Issue: Cannot import auth_service

**Solution:**
```bash
# Install missing dependencies
pip install PyJWT==2.8.0 passlib[bcrypt]==1.7.4

# Restart the server
```

## Testing Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] JWT_SECRET_KEY generated and added to .env
- [ ] SES_SENDER_EMAIL verified in AWS SES
- [ ] IAM permissions updated for SES
- [ ] Server running (`python main.py`)
- [ ] Test script runs successfully (`python test_auth_apis.py`)
- [ ] Can register new user
- [ ] Can login with registered user
- [ ] Can request password reset
- [ ] Receive OTP email (if SES configured)

## Next Steps

### 1. Frontend Integration

Use the authentication endpoints in your frontend:

```javascript
// Register
const response = await fetch('/api/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'pass123',
    full_name: 'John Doe'
  })
});

const data = await response.json();
localStorage.setItem('token', data.token);

// Use user initials in UI
document.getElementById('avatar').textContent = data.user.initials;
```

### 2. Protect Existing Endpoints

Add authentication to your upload endpoint:

```python
from fastapi import Depends
from .routes import verify_token

@router.post("/analyze/upload")
async def analyze_upload(
    ...,
    token_data: dict = Depends(verify_token)
):
    user_id = token_data['user_id']
    # Use authenticated user_id
    ...
```

### 3. Customize Email Templates

Edit `auth_service.py` line ~183 to customize OTP email:

```python
body_html = f"""
<html>
  <!-- Your custom HTML email template -->
  <h1>Your OTP: {otp_code}</h1>
</html>
"""
```

### 4. Monitor Authentication

Check logs for authentication events:

```bash
# View authentication logs
tail -f logs/api_routes.log | grep auth

# Filter by email
tail -f logs/api_routes.log | grep "user@example.com"
```

## Production Deployment

Before deploying to production:

1. **Generate Strong JWT Secret:**
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

2. **Request SES Production Access**
   - Removes sandbox limitations
   - Can send to any email

3. **Enable HTTPS**
   - Required for secure token transmission
   - Use SSL/TLS certificate

4. **Configure CORS**
   - Update allowed origins in `main.py`
   - Restrict to your frontend domain

5. **Set Up Monitoring**
   - CloudWatch for SES delivery
   - Failed login attempt alerts
   - Token expiration monitoring

6. **Add Rate Limiting**
   - Prevent brute force attacks
   - Limit password reset requests

## Support & Documentation

- **Full Documentation:** `AUTHENTICATION_DOCUMENTATION.md`
- **API Documentation:** `http://localhost:8000/docs`
- **Test Script:** `python test_auth_apis.py`
- **AWS SES Console:** https://console.aws.amazon.com/ses/
- **DynamoDB Console:** https://console.aws.amazon.com/dynamodb/

## Summary

You've successfully set up:
- ✅ User registration with email and password
- ✅ Secure login with JWT tokens
- ✅ Password reset via email OTP
- ✅ User profiles with initials for UI
- ✅ Single DynamoDB table design
- ✅ AWS SES email integration

The system is ready for frontend integration!
