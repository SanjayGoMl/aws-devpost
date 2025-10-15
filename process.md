# AWS Image and Excel Analysis Service Documentation

## Project Overview
This service provides a unified API for analyzing images and Excel files using AWS services (S3, Bedrock, and DynamoDB). It implements a 4-agent architecture for efficient file processing and analysis.

## Recent Updates (October 15, 2025)
- **Fixed Critical File Stream Issue**: Resolved "I/O operation on closed file" errors by implementing content preservation strategy
- **Enhanced Storage Agent**: Now preserves both Excel and image binary content for analysis phases
- **Improved Image Analysis Agent**: Uses stored image content instead of consuming file streams
- **Fixed JSON Serialization**: Removed binary content from API responses to prevent UTF-8 decoding errors
- **Optimized Agent Communication**: Agents now pass structured data instead of file objects

## Technical Architecture

### Components
1. **FastAPI Backend**
   - Main application entry point
   - Unified RESTful API endpoint
   - Comprehensive error handling and logging
   - CORS middleware for cross-origin requests

2. **AWS Services Integration**
   - S3: File storage with organized folder structure
   - Bedrock: Claude-3 multimodal AI analysis
   - DynamoDB: User-specific metadata and results storage

3. **4-Agent Architecture**
   - **Agent 1**: S3 Storage Agent - File upload and organization
   - **Agent 2**: Image Analysis Agent - Bedrock-powered image analysis
   - **Agent 3**: Excel Analysis Agent - Data validation and insights
   - **Agent 4**: DynamoDB Storage Agent - Result consolidation and storage

4. **Project Structure**
```
AWS_October/
├── src/
│   ├── api/
│   │   └── routes.py          # Unified API endpoint
│   ├── services/
│   │   └── aws_service.py     # 4-agent AWS integration
│   └── utils/
│       ├── logger.py          # Logging utilities
│       └── exceptions.py      # Custom exception handling
├── logs/                      # Application logs
├── main.py                    # Application entry with middleware
├── requirements.txt           # Dependencies
└── .env                      # Configuration
```

## API Endpoints

### 1. Unified Upload and Analysis (`/api/analyze/upload`)
- **Method**: POST
- **Purpose**: Analyze images and/or Excel files in a single request
- **Parameters**:
  - `user_id` (form field, required): User identifier
  - `title` (form field, optional): Project title
  - `context` (form field, optional): Context applicable to all files
  - `images` (form files, optional): Multiple image files
  - `excel` (form file, optional): Excel document
  
- **4-Agent Process**:
  1. **Storage Agent**: Validates and uploads files to S3
  2. **Image Analysis Agent**: Processes images with Bedrock
  3. **Excel Analysis Agent**: Validates and analyzes Excel data
  4. **DynamoDB Agent**: Consolidates and stores all results

### 2. Health Check (`/api/health`)
- **Method**: GET
- **Purpose**: Service health monitoring

### 3. User Projects (`/api/projects/{user_id}`)
- **Method**: GET
- **Purpose**: Retrieve user's project history

## Data Storage

### S3 Structure
```
bucket/
├── timestamp_title/
│   ├── images/
│   │   ├── image1.jpg
│   │   └── image2.jpg
│   └── excel/
│       └── data.xlsx
```

### DynamoDB Schema
- **Table Name**: upload_docs
- **Primary Key**: pk (Partition Key), sk (Sort Key)
- **User-Centric Schema**:
  ```json
  {
    "pk": "USER#12345",
    "sk": "PROJECT#20251015_DisasterRecovery",
    "title": "Disaster Recovery",
    "folder_name": "20251015_DisasterRecovery",
    "created_at": "2025-10-15T16:00:00Z",
    "context": "User-provided context text",
    "images": [
      {
        "filename": "image1.jpg",
        "s3_url": "s3://bucket/20251015_DisasterRecovery/images/image1.jpg",
        "context": "context text",
        "analysis_result": "Bedrock analysis result"
      }
    ],
    "excel": {
      "filename": "data.xlsx",
      "s3_url": "s3://bucket/20251015_DisasterRecovery/excel/data.xlsx",
      "context": "context text",
      "insights": [
        {"row_index": 0, "summary": "Row analysis"},
        {"row_index": 1, "summary": "Row analysis"}
      ],
      "analysis_result": "Overall Excel analysis"
    }
  }
  ```

## Agent Architecture Details

### Agent 1: S3 Storage Agent
**Purpose**: Store all uploaded files into S3 with organized structure
- Validates file types (images: image/*, Excel: application/vnd.ms-excel, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
- Creates timestamp-based folder structure
- **Content Preservation**: Reads and stores file binary content before upload for subsequent analysis
- **Stream Management**: Resets file pointers after reading to enable S3 upload
- Returns structured file metadata with preserved content for other agents
- Handles upload failures gracefully

### Agent 2: Image Analysis Agent
**Purpose**: Process images using AWS Bedrock Claude-3 multimodal capabilities
- **Content-Based Processing**: Uses stored image binary content instead of file streams
- Processes multiple images with context
- Uses Claude-3's vision capabilities for detailed analysis
- **Dual Analysis Methods**: Supports both UploadFile objects and binary content
- Handles image encoding and API communication
- Returns structured analysis results with filename matching

### Agent 3: Excel Analysis Agent
**Purpose**: Excel data validation and insights generation
- **Stream-Safe Processing**: Uses stored Excel binary content from Storage Agent
- Reads and validates Excel structure using pandas
- Processes data rows for insights (limited to first 5-10 rows for performance)
- Generates summaries and recommendations using Bedrock
- **Comprehensive Analysis**: Provides row counts, column analysis, and data patterns
- Handles Excel parsing errors gracefully

### Agent 4: DynamoDB Storage Agent
**Purpose**: Consolidate all agent outputs and store in DynamoDB
- Creates user-specific project records
- Combines image and Excel analysis results
- Maintains data consistency across agents
- Supports project history tracking

## Error Handling & Logging

### Fixed Critical Issues
1. **File Stream Management**: Resolved "I/O operation on closed file" errors through content preservation
2. **UTF-8 Decoding Errors**: Fixed JSON serialization by excluding binary content from responses
3. **Agent Communication**: Improved data passing between agents to prevent stream conflicts

### Exception Hierarchy
1. **ServiceException**: Base exception for service errors
2. **ValidationException**: Input validation errors (400)
3. **StorageException**: S3 storage errors (500)
4. **AnalysisException**: Bedrock analysis errors (503)
5. **DatabaseException**: DynamoDB errors (500)
6. **FileProcessingException**: File processing errors (400)
7. **AgentException**: Agent-specific errors (500)
8. **StreamException**: File stream management errors (resolved)

### Logging Strategy
- **File Logging**: Separate log files for each component
- **Console Logging**: Real-time monitoring
- **Structured Logging**: JSON-formatted logs with context
- **Error Tracking**: Full stack traces for debugging
- **Performance Logging**: Request timing and metrics

### HTTP Status Codes
- **200**: Success
- **400**: Bad request/Invalid input/Validation errors
- **500**: Internal server error/Storage/Database errors
- **503**: Service unavailable/Bedrock model errors

## Setup and Configuration

### Environment Variables
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_bucket_name
DYNAMODB_TABLE_NAME=upload_docs
BEDROCK_INFERENCE_PROFILE_ARN_ID=your_inference_profile_arn
```

### Dependencies
```txt
fastapi==0.104.1
python-multipart==0.0.6
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
boto3==1.34.0
pandas==2.1.4
openpyxl==3.1.2
botocore==1.34.0
typing-extensions==4.8.0
```

### Installation
```bash
# Create virtual environment
uv venv

# Activate environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -r requirements.txt
```

### AWS Setup
1. **S3 Bucket**: Create bucket with appropriate permissions
2. **DynamoDB Table**: 
   - Table name: `upload_docs`
   - Partition key: `pk` (String)
   - Sort key: `sk` (String)
3. **Bedrock Access**: Enable Claude-3 model access
4. **IAM Permissions**: Configure appropriate AWS permissions

### Running the Application
```bash
# Development mode
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python main.py
```

## Request/Response Examples

### Successful Upload Request
```bash
curl -X POST "http://localhost:8000/api/analyze/upload" \
  -F "user_id=user123" \
  -F "title=My Project" \
  -F "context=Analyzing disaster recovery images and sales data" \
  -F "images=@image1.jpg" \
  -F "images=@image2.jpg" \
  -F "excel=@data.xlsx"
```

### Successful Response
```json
{
  "status": "success",
  "folder_name": "20251015_160000_My_Project",
  "images_processed": 2,
  "excel_processed": true,
  "storage_details": {
    "folder_name": "20251015_160000_My_Project",
    "images": [
      {
        "filename": "image1.jpg",
        "s3_url": "s3://bucket/20251015_160000_My_Project/images/image1.jpg"
      }
    ],
    "excel": {
      "filename": "data.xlsx",
      "s3_url": "s3://bucket/20251015_160000_My_Project/excel/data.xlsx"
    }
  },
  "db_reference": "USER#user123#PROJECT#20251015_160000_My_Project"
}
```

## Error Handling Examples

### Validation Error Response
```json
{
  "error": "VALIDATION_ERROR",
  "message": "File image.txt is not a valid image",
  "details": {
    "field": "images",
    "file_type": "text/plain"
  }
}
```

### Service Error Response
```json
{
  "error": "STORAGE_ERROR",
  "message": "Failed to upload file to S3",
  "details": {
    "operation": "upload_file",
    "bucket": "my-bucket"
  }
}
```

## Monitoring and Observability

### Log Files Structure
```
logs/
├── main_2025-10-15.log           # Main application logs
├── api_routes_2025-10-15.log     # API endpoint logs
├── aws_service_2025-10-15.log    # AWS service logs
├── storage_agent_2025-10-15.log  # Storage operations
├── image_agent_2025-10-15.log    # Image analysis logs
├── excel_agent_2025-10-15.log    # Excel processing logs
└── dynamodb_agent_2025-10-15.log # Database operations
```

### Health Monitoring
- **Endpoint**: `/api/health`
- **Response**: Service status and component health
- **Metrics**: Request counts, response times, error rates

### Performance Considerations
1. **File Size Limits**: Configure appropriate limits for uploads
2. **Concurrent Processing**: Agent-based architecture supports parallel processing
3. **Memory Management**: Efficient file handling with streaming
4. **Rate Limiting**: Implement request throttling for production

## Security Best Practices
1. **AWS IAM**: Principle of least privilege
2. **Input Validation**: Strict file type and size validation
3. **Error Sanitization**: No sensitive data in error messages
4. **Logging Security**: No credentials or PII in logs
5. **CORS Configuration**: Restrict origins in production

## Deployment Considerations
1. **Environment Separation**: Different configs for dev/staging/prod
2. **Secret Management**: Use AWS Secrets Manager or similar
3. **Load Balancing**: Multiple instances for high availability
4. **Database Scaling**: Configure DynamoDB auto-scaling
5. **Monitoring**: CloudWatch integration for AWS metrics

## Testing Strategy
1. **Unit Tests**: Individual agent testing
2. **Integration Tests**: End-to-end workflow testing
3. **Load Tests**: Performance under concurrent requests
4. **Error Tests**: Failure scenario validation

## Current Status (October 15, 2025)

### ✅ Issues Resolved
1. **File Stream Errors**: Fixed "I/O operation on closed file" for both Excel and Image Analysis Agents
2. **UTF-8 Decoding Errors**: Resolved JSON serialization issues by excluding binary content from responses
3. **Agent Communication**: Improved data flow between agents using structured content preservation
4. **Server Stability**: All 4 agents now working correctly without stream conflicts

### 🚀 System Status
- **Server**: Running successfully on http://localhost:8000
- **API Endpoint**: `/api/analyze/upload` fully operational
- **Swagger UI**: Available at http://localhost:8000/docs
- **All Agents**: Storage ✅, Image Analysis ✅, Excel Analysis ✅, DynamoDB Storage ✅

### 🧪 Testing Results
- Excel Analysis Agent: Successfully processes Excel files
- Image Analysis Agent: Fixed stream issues, ready for testing
- Storage Agent: Enhanced with content preservation
- DynamoDB Agent: Consolidates results correctly

## Technical Implementation Details

### File Stream Management Solution
**Problem**: File streams were being consumed during S3 upload, causing "I/O operation on closed file" errors in analysis phases.

**Solution**: 
```python
# Storage Agent now preserves content
excel_content = await excel.read()  # Read content first
await excel.seek(0)                 # Reset for upload
result["excel_content"] = excel_content  # Store for analysis

# Analysis Agents use stored content
excel_bytes = storage_result.get("excel_content")
df = pd.read_excel(io.BytesIO(excel_bytes))
```

### Agent Architecture Improvements
1. **Storage Agent**: Enhanced with content preservation (`image_contents`, `excel_content`)
2. **Image Analysis Agent**: New `_analyze_with_bedrock_content()` method for binary content
3. **Excel Analysis Agent**: Stream-safe processing using stored bytes
4. **Response Sanitization**: Binary content excluded from JSON responses

### Performance Optimizations
- **Memory Efficient**: Content read once and reused across agents
- **Stream Safety**: No file pointer conflicts between agents
- **Error Resilience**: Graceful handling of malformed files
- **JSON Serialization**: Clean responses without binary data

## Future Enhancements
1. **Authentication**: JWT-based user authentication
2. **Rate Limiting**: Request throttling per user
3. **Caching**: Redis for frequent queries and stored content
4. **Batch Processing**: Multiple file batch uploads with parallel processing
5. **Webhooks**: Async processing notifications
6. **API Versioning**: Support for multiple API versions
7. **Metrics Dashboard**: Real-time monitoring interface
8. **File Preview**: Generate thumbnails and previews
9. **Content Streaming**: Large file processing with streaming support
10. **Advanced Error Recovery**: Retry mechanisms for failed agent operations