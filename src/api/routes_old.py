from fastapi import APIRouter, UploadFile, Form, File, HTTPException
from typing import List
import pandas as pd
import logging
from ..services.aws_service import AWSService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
aws_service = AWSService()

@router.post("/analyze/images")
async def analyze_images(
    title: str = Form(...),
    images: List[UploadFile] = File(...)
):
    try:
        if not images:
            raise HTTPException(
                status_code=400,
                detail="No images provided"
            )
        
        # Validate file types
        for image in images:
            if not image.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {image.filename} is not a valid image"
                )
        
        logger.info(f"Processing {len(images)} images for title: {title}")
        
        # Get or create folder for this title
        folder_name = await aws_service.get_or_create_folder(title)
        
        image_descriptions = []
        image_urls = []
        
        for idx, image in enumerate(images):
            logger.info(f"Processing image {idx + 1}/{len(images)}: {image.filename}")
            
            try:
                image_url = await aws_service.upload_file_to_s3(
                    image.file, 
                    folder_name,
                    'images', 
                    f"{idx}_{image.filename}"
                )
                image_urls.append(image_url)
                
                prompt = f"Please describe this image in detail: {image_url}"
                description = await aws_service.analyze_with_bedrock(prompt)
                image_descriptions.append(description)
                
                logger.info(f"Successfully processed image {idx + 1}")
                
            except Exception as e:
                logger.error(f"Error processing image {image.filename}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing image {image.filename}"
                )
        
        # Save analysis to DynamoDB
        analysis_data = {
            'image_urls': image_urls,
            'descriptions': image_descriptions
        }
        
        await aws_service.save_analysis_to_dynamodb(
            folder_name=folder_name,
            title=title,
            analysis_type='image_analysis',
            data=analysis_data
        )
        
        logger.info(f"Successfully completed analysis for {len(images)} images")
        
        return {
            'status': 'success',
            'folder': folder_name,
            'descriptions': image_descriptions
        }
        
    except HTTPException as e:
        # Re-raise HTTP exceptions as they already have the correct format
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_images: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during image analysis"
        )

@router.post("/analyze/excel")
async def analyze_excel(
    title: str = Form(...),
    excel_file: UploadFile = File(...)
):
    try:
        # Validate file type
        if not excel_file.content_type in [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]:
            raise HTTPException(
                status_code=400,
                detail="File must be an Excel document"
            )
        
        logger.info(f"Processing Excel file {excel_file.filename} for title: {title}")
        
        # Get or create folder for this title
        folder_name = await aws_service.get_or_create_folder(title)
        
        # Upload to S3
        try:
            excel_url = await aws_service.upload_file_to_s3(
                excel_file.file,
                folder_name,
                'excel',
                excel_file.filename
            )
        except Exception as e:
            logger.error(f"Error uploading Excel file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to upload Excel file"
            )
        
        # Read Excel content
        try:
            df = pd.read_excel(excel_file.file)
            excel_content = df.to_string()
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Invalid Excel file format"
            )
        
        # Analyze with Bedrock
        prompt = f"Please analyze and summarize this Excel data: {excel_content}"
        analysis = await aws_service.analyze_with_bedrock(prompt)
        
        # Save analysis to DynamoDB
        analysis_data = {
            'excel_url': excel_url,
            'analysis': analysis
        }
        
        await aws_service.save_analysis_to_dynamodb(
            folder_name=folder_name,
            title=title,
            analysis_type='excel_analysis',
            data=analysis_data
        )
        
        logger.info(f"Successfully completed analysis for Excel file {excel_file.filename}")
        
        return {
            'status': 'success',
            'folder': folder_name,
            'analysis': analysis
        }
        
    except HTTPException as e:
        # Re-raise HTTP exceptions as they already have the correct format
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_excel: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during Excel analysis"
        )