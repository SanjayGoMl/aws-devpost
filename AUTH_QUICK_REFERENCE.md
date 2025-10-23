# Authentication System - Quick Reference

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
pip install PyJWT==2.8.0 passlib[bcrypt]==1.7.4
```

### 2. Generate JWT Secret
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Update .env
```bash
JWT_SECRET_KEY=<paste-generated-secret-here>
JWT_EXPIRATION_HOURS=24
SES_SENDER_EMAIL=noreply@yourdomain.com
SES_SENDER_NAME=AWS Analysis Service
```

### 4. Verify AWS SES Email
- Go to: https://console.aws.amazon.com/ses/
- Verified Identities → Create Identity
- Enter your sender email
- Check inbox and verify

### 5. Test
```bash
python3 test_auth_apis.py
```

---

## 📋 API Endpoints

### Register
```bash
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe"
}
```

### Login
```bash
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

### Request Password Reset
```bash
POST /api/auth/request-password-reset
{
  "email": "user@example.com"
}
```

### Reset Password
```bash
POST /api/auth/verify-reset
{
  "email": "user@example.com",
  "otp": "123456",
  "new_password": "NewPass456"
}
```

---

## 📂 Files Added/Modified

### New Files
- ✅ `src/services/auth_service.py` - Authentication logic
- ✅ `src/api/auth_models.py` - Pydantic models
- ✅ `test_auth_apis.py` - Test suite
- ✅ `AUTHENTICATION_DOCUMENTATION.md` - Full docs
- ✅ `AUTHENTICATION_SETUP.md` - Setup guide
- ✅ `IMPLEMENTATION_SUMMARY.md` - What was done

### Modified Files
- ✅ `src/api/routes.py` - Added auth endpoints
- ✅ `main.py` - Updated root info
- ✅ `requirements.txt` - Added dependencies
- ✅ `.env.example` - Added auth config

---

## 🔧 Environment Variables

### Required
```bash
JWT_SECRET_KEY=your-32-char-secret
JWT_EXPIRATION_HOURS=24
SES_SENDER_EMAIL=noreply@yourdomain.com
SES_SENDER_NAME=Your App Name
```

### Existing (No Changes)
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=your_table
```

---

## 💾 DynamoDB Structure

### User Profile (NEW)
```
pk: "USER#{user_id}"
sk: "PROFILE"
email, full_name, password_hash, created_at, last_login
```

### Projects (Existing)
```
pk: "USER#{user_id}"
sk: "PROJECT#{folder_name}"
title, folder_name, images, excel, documents
```

**Note:** `user_id` = first 12 chars of SHA256(email)

---

## 🧪 Testing

```bash
# Run test suite
python3 test_auth_apis.py

# Expected: 6/6 tests passed
```

---

## 🔐 Security Features

- ✅ Bcrypt password hashing
- ✅ JWT tokens (24hr expiry)
- ✅ Email OTP (10min expiry)
- ✅ User ID privacy (SHA256 hash)
- ✅ Secure random OTP generation
- ✅ Input validation

---

## 💻 Frontend Integration

### Register
```javascript
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

// Show initials in avatar
document.getElementById('avatar').textContent = data.user.initials; // "JD"
```

### Login
```javascript
const response = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'pass123'
  })
});

const data = await response.json();
localStorage.setItem('token', data.token);
```

### Use Token
```javascript
const token = localStorage.getItem('token');

fetch('/api/projects/user123', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Password Reset
```javascript
// Step 1: Request OTP
await fetch('/api/auth/request-password-reset', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'user@example.com' })
});

// User receives email with OTP

// Step 2: Reset with OTP
await fetch('/api/auth/verify-reset', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    otp: '123456',
    new_password: 'newpass123'
  })
});
```

---

## 🎨 UI Avatar Component

```html
<div class="avatar">JD</div>

<style>
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #4CAF50;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}
</style>
```

---

## 🐛 Common Issues

### "JWT_SECRET_KEY must be configured"
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Add output to .env as JWT_SECRET_KEY
```

### "Email address not verified"
- Verify sender email in AWS SES Console
- In sandbox: verify recipient emails too

### "Import error: jwt"
```bash
pip install PyJWT==2.8.0 passlib[bcrypt]==1.7.4
```

### Email not received
- Check spam folder
- Verify SES sandbox mode (recipients must be verified)
- Check SES sending statistics in AWS Console

---

## 📚 Documentation

- **Full Docs:** `AUTHENTICATION_DOCUMENTATION.md`
- **Setup Guide:** `AUTHENTICATION_SETUP.md`
- **Implementation:** `IMPLEMENTATION_SUMMARY.md`
- **API Docs:** http://localhost:8000/docs

---

## ✅ Deployment Checklist

- [ ] Install dependencies
- [ ] Generate JWT secret
- [ ] Update .env
- [ ] Verify SES sender email
- [ ] Add SES IAM permissions
- [ ] Test locally
- [ ] Request SES production access (optional)
- [ ] Enable HTTPS
- [ ] Configure CORS
- [ ] Deploy!

---

## 🎯 What You Get

✅ User registration with email/password  
✅ Secure login with JWT tokens  
✅ Password reset via email OTP  
✅ User profiles with initials for UI  
✅ Single DynamoDB table design  
✅ Complete test suite  
✅ Comprehensive documentation  
✅ Frontend integration examples  

**Ready to use! 🚀**

---

## 📞 Need Help?

1. Check `AUTHENTICATION_SETUP.md` for detailed setup
2. Check `AUTHENTICATION_DOCUMENTATION.md` for architecture
3. Run `python3 test_auth_apis.py` to verify setup
4. Check AWS SES console for email delivery status
5. Check logs in `logs/` directory

---

**Last Updated:** October 23, 2025  
**Version:** 1.0.0  
**Status:** ✅ Production Ready
