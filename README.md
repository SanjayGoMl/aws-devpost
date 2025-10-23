# AWS Image and Excel Analysis Service

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20S3%20%7C%20DynamoDB-orange.svg)](https://aws.amazon.com)
[![UV](https://img.shields.io/badge/uv-package%20manager-6B46C1.svg)](https://github.com/astral-sh/uv)

A unified API service for analyzing images and Excel files using AWS Bedrock (Claude-3), S3 storage, and DynamoDB. Built with a 4-agent architecture for efficient file processing and AI-powered analysis.

## 🚀 Features

- **User Authentication**: Secure registration, login, and password reset with JWT tokens
- **Email OTP System**: AWS SES integration for password reset verification
- **Unified API Endpoint**: Single endpoint for both image and Excel analysis
- **4-Agent Architecture**: Modular processing pipeline with specialized agents
- **AWS Bedrock Integration**: Claude-3 multimodal AI for image and text analysis
- **Secure File Storage**: Organized S3 bucket structure with timestamp-based folders
- **User-Centric Database**: DynamoDB single-table design for users and projects
- **Stream-Safe Processing**: Resolved file stream management for reliable uploads
- **Comprehensive Error Handling**: Detailed logging and graceful error recovery

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Agent 1       │    │   Agent 2       │    │   Agent 3       │    │   Agent 4       │
│  Storage Agent  │───▶│ Image Analysis  │───▶│ Excel Analysis  │───▶│ DynamoDB Storage│
│   (S3 Upload)   │    │   (Bedrock)     │    │   (Pandas +     │    │  (Consolidate)  │
│                 │    │                 │    │    Bedrock)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Prerequisites

- **Python 3.11+** installed on your system
- **UV package manager** ([installation guide](https://github.com/astral-sh/uv#installation))
- **AWS Account** with appropriate permissions
- **Git** for version control

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/SanjayGoMl/hakathon_september.git
cd AWS_October
```

### 2. Install UV (if not already installed)

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (using pip):**
```bash
pip install uv
```

### 3. Create Virtual Environment with UV

```bash
# Create virtual environment
uv venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate
```

### 4. Install Dependencies

```bash
# Install all dependencies using uv
uv pip install -r requirements.txt

# Or install individual packages with uv
uv add fastapi python-multipart uvicorn boto3 pandas openpyxl python-dotenv
```

### 5. Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env  # If example exists, or create manually
```

Add your AWS credentials and configuration:

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# AWS Services
S3_BUCKET_NAME=your-s3-bucket-name
DYNAMODB_TABLE_NAME=upload_docs
BEDROCK_INFERENCE_PROFILE_ARN_ID=arn:aws:bedrock:us-east-1:772986066238:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0

# Authentication (NEW)
JWT_SECRET_KEY=generate-using-command-below-minimum-32-chars
JWT_EXPIRATION_HOURS=24

# AWS SES for Email OTP (NEW)
SES_SENDER_EMAIL=noreply@yourdomain.com
SES_SENDER_NAME=AWS Analysis Service

# Application Settings
LOG_LEVEL=INFO
```

**Generate JWT Secret:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 6. AWS Setup

#### S3 Bucket Setup
```bash
# Create S3 bucket (replace with your bucket name)
aws s3 mb s3://your-s3-bucket-name --region us-east-1

# Set bucket policy for appropriate access
aws s3api put-bucket-policy --bucket your-s3-bucket-name --policy file://bucket-policy.json
```

#### DynamoDB Table Setup
```bash
# Create DynamoDB table
aws dynamodb create-table \
    --table-name upload_docs \
    --attribute-definitions \
        AttributeName=pk,AttributeType=S \
        AttributeName=sk,AttributeType=S \
    --key-schema \
        AttributeName=pk,KeyType=HASH \
        AttributeName=sk,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

#### AWS Bedrock Setup
1. Enable Claude-3 model access in AWS Bedrock console
2. Ensure your AWS account has bedrock permissions
3. Update the inference profile ARN in your `.env` file

#### AWS SES Setup (for Email OTP)
1. **Verify Sender Email:**
   ```bash
   # Go to AWS SES Console → Verified Identities
   # Create Identity → Email Address
   # Verify the sender email you'll use (e.g., noreply@yourdomain.com)
   ```

2. **Add IAM Permissions:**
   ```json
   {
     "Effect": "Allow",
     "Action": ["ses:SendEmail", "ses:SendRawEmail"],
     "Resource": "*"
   }
   ```

3. **Testing (Sandbox Mode):**
   - Verify recipient emails in SES Console for testing
   - Or request production access to send to any email

For detailed authentication setup, see: `AUTHENTICATION_SETUP.md`

### 7. Verify Installation

```bash
# Test Python imports and configuration
uv run python -c "
import sys
print('✅ Python version:', sys.version)

try:
    from main import app
    print('✅ Application imported successfully!')
    
    import boto3
    print('✅ AWS SDK (boto3) imported successfully!')
    
    import pandas as pd
    print('✅ Pandas imported successfully!')
    
    import fastapi
    print('✅ FastAPI imported successfully!')
    
    print('✅ All dependencies verified!')
except Exception as e:
    print('❌ Import error:', e)
"
```

## 🚀 Running the Application

### Development Mode

```bash
# Using UV with uvicorn
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Alternative: Direct Python execution
uv run python main.py
```

### Production Mode

```bash
# Using UV with production settings
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# With specific UV Python
uv run --python 3.11 uvicorn main:app --host 0.0.0.0 --port 8000
```

### Using UV Scripts (Optional)

Add to `pyproject.toml`:

```toml
[project.scripts]
start = "uvicorn main:app --host 0.0.0.0 --port 8000"
dev = "uvicorn main:app --reload --host 0.0.0.0 --port 8000"
```

Then run:
```bash
uv run start    # Production
uv run dev      # Development
```

## 🧪 Testing the API

### 1. Access Swagger UI
Open your browser and navigate to: `http://localhost:8000/docs`

### 2. Health Check
```bash
curl http://localhost:8000/api/health
```

### 3. Upload and Analyze Files
```bash
curl -X POST "http://localhost:8000/api/analyze/upload" \
  -F "user_id=test_user_001" \
  -F "title=Sample Analysis" \
  -F "context=Testing image and Excel analysis" \
  -F "images=@sample_image.jpg" \
  -F "excel=@sample_data.xlsx"
```

## 📁 Project Structure

```
aws_october/
├── src/
│   ├── agents/           # Individual agent modules (if refactored)
│   ├── api/
│   │   ├── models.py     # Pydantic models
│   │   ├── auth_models.py # Authentication models (NEW)
│   │   └── routes.py     # API endpoints (includes auth)
│   ├── services/
│   │   ├── aws_service.py # Main 4-agent implementation
│   │   └── auth_service.py # Authentication service (NEW)
│   └── utils/
│       ├── exceptions.py # Custom exceptions
│       └── logger.py     # Logging utilities
├── logs/                 # Application logs
├── public/               # Static assets
├── playground/           # Development/testing scripts
├── test_auth_apis.py    # Authentication test suite (NEW)
├── AUTHENTICATION_DOCUMENTATION.md # Full auth docs (NEW)
├── AUTHENTICATION_SETUP.md         # Auth setup guide (NEW)
├── AUTH_QUICK_REFERENCE.md         # Quick reference (NEW)
├── IMPLEMENTATION_SUMMARY.md       # Implementation details (NEW)
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
├── pyproject.toml       # UV/Python project configuration
├── uv.lock             # UV lock file
├── .env                # Environment variables (create this)
└── README.md           # This file
```

## 🔧 Development with UV

### Adding New Dependencies

```bash
# Add new package
uv add package_name

# Add development dependency
uv add --dev pytest black mypy

# Add from specific index
uv add package_name --index-url https://pypi.org/simple/
```

### Managing Python Versions

```bash
# Install specific Python version
uv python install 3.11

# Use specific Python version
uv run --python 3.11 python main.py

# Set project Python version
uv python pin 3.11
```

### Updating Dependencies

```bash
# Update all dependencies
uv pip sync requirements.txt

# Update specific package
uv add package_name --upgrade
```

## 📊 API Documentation

### Authentication Endpoints (NEW)

#### Register User
**Method:** POST  
**Endpoint:** `/api/auth/register`  
**Content-Type:** application/json

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "full_name": "John Doe"
  }'
```

**Response:**
```json
{
  "message": "Registration successful",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "user_id": "3f4a8b9c2d1e",
    "email": "user@example.com",
    "full_name": "John Doe",
    "initials": "JD"
  }
}
```

#### Login User
**Method:** POST  
**Endpoint:** `/api/auth/login`

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

#### Request Password Reset
**Method:** POST  
**Endpoint:** `/api/auth/request-password-reset`

```bash
curl -X POST "http://localhost:8000/api/auth/request-password-reset" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

#### Reset Password with OTP
**Method:** POST  
**Endpoint:** `/api/auth/verify-reset`

```bash
curl -X POST "http://localhost:8000/api/auth/verify-reset" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp": "123456",
    "new_password": "NewSecurePass456"
  }'
```

### Main Endpoint: `/api/analyze/upload`

**Method:** POST  
**Content-Type:** multipart/form-data

**Parameters:**
- `user_id` (required): User identifier string
- `title` (optional): Project title for organization
- `context` (optional): Context text for AI analysis
- `images` (optional): Multiple image files (JPEG, PNG, GIF)
- `excel` (optional): Excel file (.xlsx, .xls)

**Response:**
```json
{
  "status": "success",
  "folder_name": "20251015_143022_Sample_Analysis",
  "images_processed": 2,
  "excel_processed": true,
  "storage_details": {
    "folder_name": "20251015_143022_Sample_Analysis",
    "images": [
      {
        "filename": "image1.jpg",
        "s3_url": "s3://bucket/20251015_143022_Sample_Analysis/images/image1.jpg"
      }
    ],
    "excel": {
      "filename": "data.xlsx",
      "s3_url": "s3://bucket/20251015_143022_Sample_Analysis/excel/data.xlsx"
    }
  },
  "db_reference": "USER#test_user_001#PROJECT#20251015_143022_Sample_Analysis"
}
```

## 🐛 Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   ```bash
   # Verify AWS configuration
   aws configure list
   aws sts get-caller-identity
   ```

2. **UV Command Not Found**
   ```bash
   # Reinstall UV
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc  # or restart terminal
   ```

3. **Import Errors**
   ```bash
   # Reinstall dependencies
   uv pip sync requirements.txt --force-reinstall
   ```

4. **Port Already in Use**
   ```bash
   # Find and kill process using port 8000
   lsof -ti:8000 | xargs kill -9
   ```

### Logs Location
Check logs in the `logs/` directory:
- `main.log` - Application logs
- `aws_service.log` - AWS service operations
- `api_routes.log` - API endpoint logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes using UV for dependency management
4. Test your changes: `uv run python -m pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/SanjayGoMl/hakathon_september/issues)
- **Documentation**: [process.md](process.md) for detailed technical documentation
- **AWS Documentation**: [AWS Bedrock](https://docs.aws.amazon.com/bedrock/), [S3](https://docs.aws.amazon.com/s3/), [DynamoDB](https://docs.aws.amazon.com/dynamodb/)

## 🏆 Acknowledgments

- **AWS Bedrock** for Claude-3 multimodal AI capabilities
- **UV** for fast and reliable Python package management
- **FastAPI** for the high-performance web framework
- **Pandas** for Excel data processing

---

**Last Updated:** October 15, 2025  
**Version:** 1.0.0  
**Python Version:** 3.11+  
**UV Version:** Latest
