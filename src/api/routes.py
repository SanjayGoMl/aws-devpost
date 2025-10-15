from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import List, Optional
import logging
from ..services.aws_service import AWSService
from .models import UserProjectsResponse, ProjectDetailsResponse, UsersCountResponse, ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api_routes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

router = APIRouter()
aws_service = AWSService()

@router.post("/analyze/upload")
async def analyze_upload(
    user_id: str = Form(..., description="Required user identifier"),
    title: str = Form("", description="Optional project title"),
    context: str = Form("", description="Optional context text applicable to all files"),
    image_descriptions: List[str] = Form(default=[], description="Optional descriptions for each uploaded image (by upload order)"),
    images: List[UploadFile] = File(default=None, description="Multiple image files (JPG, PNG, etc.)"),
    excel: UploadFile = File(default=None, description="Excel document (.xls, .xlsx)"),
    documents: List[UploadFile] = File(default=None, description="Multiple document files (.txt, .pdf)")
):
    """
    ## Unified endpoint for analyzing images, Excel files, and documents using AWS Bedrock
    
    ### Parameters:
    - **user_id** (required): User identifier for tracking projects
    - **title** (optional): Project title for organization
    - **context** (optional): Context text that will be applied to all file analyses
    - **image_descriptions** (optional): Array of descriptions for each uploaded image (mapped by upload order)
    - **images** (optional): Multiple image files for analysis
    - **excel** (optional): Excel document for data analysis
    - **documents** (optional): Multiple document files for text analysis
    
    ### Image Description Mapping:
    - **Order-based**: image_descriptions[0] applies to images[0], image_descriptions[1] applies to images[1], etc.
    - **Flexible length**: If fewer descriptions than images, remaining images get no specific description
    - **Example**: 3 images + ["Desc1", "Desc2"] → Image1 gets "Desc1", Image2 gets "Desc2", Image3 gets no description
    
    ### File Requirements:
    - **Images**: Supported formats - JPG, JPEG, PNG, GIF, BMP, WEBP
    - **Excel**: Supported formats - .xls, .xlsx
    - **Documents**: Supported formats - .txt, .pdf
    - **Note**: At least one file (image, Excel, or document) must be provided
    
    ### Response:
    Returns processing results including S3 URLs, analysis results, and DynamoDB references.
    """
    try:
        logger.info(f"Starting upload analysis for user {user_id}")
        
        # Validate input - check if files were actually uploaded
        has_images = images and len(images) > 0 and any(img.filename for img in images)
        has_excel = excel and excel.filename
        has_documents = documents and len(documents) > 0 and any(doc.filename for doc in documents)
        
        if not has_images and not has_excel and not has_documents:
            raise HTTPException(
                status_code=400,
                detail="At least one file (image, Excel, or document) must be provided"
            )
        
        # Validate images if provided
        if has_images:
            valid_image_types = [
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
                'image/bmp', 'image/webp', 'image/tiff'
            ]
            for idx, image in enumerate(images):
                if image and image.filename:  # Only validate if file was actually uploaded
                    if not image.content_type or image.content_type not in valid_image_types:
                        logger.warning(f"Invalid image type for file {idx}: {image.content_type}")
                        raise HTTPException(
                            status_code=400,
                            detail=f"File {image.filename} is not a valid image. Supported formats: JPG, PNG, GIF, BMP, WEBP, TIFF"
                        )
        
        # Validate Excel if provided
        if has_excel:
            valid_excel_types = [
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/octet-stream'  # Sometimes Excel files are detected as this
            ]
            # Also check file extension as a fallback
            excel_extensions = ['.xls', '.xlsx']
            is_valid_excel = (
                (excel.content_type and excel.content_type in valid_excel_types) or
                (excel.filename and any(excel.filename.lower().endswith(ext) for ext in excel_extensions))
            )
            
            if not is_valid_excel:
                logger.warning(f"Invalid Excel type: {excel.content_type}, filename: {excel.filename}")
                raise HTTPException(
                    status_code=400,
                    detail="Excel file must be a valid Excel document (.xls or .xlsx)"
                )
        
        # Validate documents if provided
        if has_documents:
            valid_document_types = [
                'text/plain',
                'application/pdf',
                'application/octet-stream'  # Sometimes files are detected as this
            ]
            # Also check file extension as a fallback
            document_extensions = ['.txt', '.pdf']
            
            for idx, document in enumerate(documents):
                if document and document.filename:  # Only validate if file was actually uploaded
                    is_valid_document = (
                        (document.content_type and document.content_type in valid_document_types) or
                        (document.filename and any(document.filename.lower().endswith(ext) for ext in document_extensions))
                    )
                    
                    if not is_valid_document:
                        logger.warning(f"Invalid document type for file {idx}: {document.content_type}, filename: {document.filename}")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Document {document.filename} must be a valid text or PDF file (.txt or .pdf)"
                        )
        
        # Filter out empty uploads
        valid_images = [img for img in (images or []) if img and img.filename]
        valid_excel = excel if excel and excel.filename else None  
        valid_documents = [doc for doc in (documents or []) if doc and doc.filename]
        
        logger.info(f"Validation passed. Processing {len(valid_images)} images, {'1 Excel file' if valid_excel else 'no Excel file'}, and {len(valid_documents)} documents")
        
        # Process upload using the enhanced 5-agent architecture
        result = await aws_service.process_upload(
            user_id=user_id,
            title=title if title else None,
            images=valid_images,
            excel=valid_excel,
            documents=valid_documents,
            context=context,
            image_descriptions=image_descriptions
        )
        
        logger.info(f"Successfully completed upload analysis for user {user_id}")
        return result
        
    except HTTPException as e:
        logger.error(f"HTTP error in analyze_upload: {e.detail}")
        raise e
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during upload analysis"
        )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "service": "AWS Image and Excel Analysis Service",
            "timestamp": "2025-10-15"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

@router.get("/projects/{user_id}", response_model=UserProjectsResponse)
async def get_user_projects(
    user_id: str,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of projects to return")
):
    """
    ## Get all projects for a specific user
    
    Retrieves a list of all projects created by the specified user from DynamoDB.
    Projects are returned in descending order by creation date (newest first).
    
    ### Parameters:
    - **user_id** (required): User identifier to retrieve projects for
    - **limit** (optional): Maximum number of projects to return (default: 50, max: 100)
    
    ### Response:
    Returns a list of project summaries including:
    - Project metadata (title, creation date, folder name)
    - File counts and types (images, Excel)
    - Analysis completion status
    - S3 storage URLs for files
    
    ### Example Usage:
    ```
    GET /api/projects/user123?limit=20
    ```
    """
    try:
        logger.info(f"Retrieving projects for user {user_id} with limit {limit}")
        
        # Validate user_id
        if not user_id or len(user_id.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="User ID cannot be empty"
            )
        
        # Call AWS service to get projects
        result = await aws_service.get_user_projects(user_id.strip(), limit)
        
        logger.info(f"Successfully retrieved {result['total_projects']} projects for user {user_id}")
        return result
        
    except HTTPException as e:
        logger.error(f"HTTP error retrieving projects for user {user_id}: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error retrieving projects for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving user projects"
        )

@router.get("/projects/{user_id}/{project_id}", response_model=ProjectDetailsResponse)
async def get_project_details(user_id: str, project_id: str):
    """
    ## Get detailed information for a specific project
    
    Retrieves complete project details including full analysis results,
    file metadata, and AI-generated insights for both images and Excel data.
    
    ### Parameters:
    - **user_id** (required): User identifier who owns the project
    - **project_id** (required): Project identifier (folder name)
    
    ### Response:
    Returns detailed project information including:
    - Complete image analysis results from AWS Bedrock
    - Full Excel analysis including data insights and recommendations
    - File storage information and S3 URLs
    - Project metadata and context
    
    ### Example Usage:
    ```
    GET /api/projects/user123/20251015_143022_Sample_Analysis
    ```
    """
    try:
        logger.info(f"Retrieving project details for user {user_id}, project {project_id}")
        
        # Validate input parameters
        if not user_id or len(user_id.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="User ID cannot be empty"
            )
        
        if not project_id or len(project_id.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Project ID cannot be empty"
            )
        
        # Call AWS service to get project details
        result = await aws_service.get_project_details(user_id.strip(), project_id.strip())
        
        logger.info(f"Successfully retrieved project details for {project_id}")
        return result
        
    except HTTPException as e:
        logger.error(f"HTTP error retrieving project details: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error retrieving project details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving project details"
        )

@router.get("/users/count", response_model=UsersCountResponse)
async def get_total_users():
    """
    ## Get total number of unique users
    
    Returns the total count of unique users (PKs) in the system.
    This endpoint scans the DynamoDB table to count all unique USER# entries.
    
    ### Response:
    Returns the total count of unique users and optionally their user IDs.
    
    ### Example Usage:
    ```
    GET /api/users/count
    ```
    """
    try:
        logger.info("Getting total users count")
        
        # Call AWS service to get users count
        result = await aws_service.get_total_users()
        
        logger.info(f"Successfully retrieved users count: {result['total_unique_users']}")
        return result
        
    except HTTPException as e:
        logger.error(f"HTTP error getting users count: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error getting users count: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while getting users count"
        )