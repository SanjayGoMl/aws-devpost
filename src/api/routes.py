from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
import logging
from ..services.aws_service import AWSService

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
    images: List[UploadFile] = File(description="Multiple image files (JPG, PNG, etc.)"),
    excel: UploadFile = File(description="Excel document (.xls, .xlsx)")
):
    """
    ## Unified endpoint for analyzing images and Excel files using AWS Bedrock
    
    ### Parameters:
    - **user_id** (required): User identifier for tracking projects
    - **title** (optional): Project title for organization
    - **context** (optional): Context text that will be applied to all file analyses
    - **images** (optional): Multiple image files for analysis
    - **excel** (optional): Excel document for data analysis
    
    ### File Requirements:
    - **Images**: Supported formats - JPG, JPEG, PNG, GIF, BMP, WEBP
    - **Excel**: Supported formats - .xls, .xlsx
    - **Note**: At least one image or Excel file must be provided
    
    ### Response:
    Returns processing results including S3 URLs, analysis results, and DynamoDB references.
    """
    try:
        logger.info(f"Starting upload analysis for user {user_id}")
        
        # Validate input - check if files were actually uploaded
        has_images = len(images) > 0 and any(img.filename for img in images)
        has_excel = excel and excel.filename
        
        if not has_images and not has_excel:
            raise HTTPException(
                status_code=400,
                detail="At least one image or Excel file must be provided"
            )
        
        # Validate images if provided
        if has_images:
            valid_image_types = [
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
                'image/bmp', 'image/webp', 'image/tiff'
            ]
            for idx, image in enumerate(images):
                if image.filename:  # Only validate if file was actually uploaded
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
        
        # Filter out empty uploads
        valid_images = [img for img in images if img.filename]
        valid_excel = excel if excel and excel.filename else None
        
        logger.info(f"Validation passed. Processing {len(valid_images)} images and {'1 Excel file' if valid_excel else 'no Excel file'}")
        
        # Process upload using the 4-agent architecture
        result = await aws_service.process_upload(
            user_id=user_id,
            title=title if title else None,
            images=valid_images,
            excel=valid_excel,
            context=context
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

@router.get("/projects/{user_id}")
async def get_user_projects(user_id: str):
    """Get all projects for a specific user"""
    try:
        # This would be implemented to query DynamoDB for user projects
        # For now, return a placeholder response
        logger.info(f"Retrieving projects for user {user_id}")
        return {
            "user_id": user_id,
            "projects": [],
            "message": "Project retrieval endpoint - to be implemented"
        }
    except Exception as e:
        logger.error(f"Error retrieving projects for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving user projects"
        )