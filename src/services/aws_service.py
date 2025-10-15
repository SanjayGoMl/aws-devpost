import os
import json
import re
import boto3
import logging
import base64
import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/aws_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class AWSService:
    def __init__(self):
        aws_config = {
            "aws_access_key_id": os.getenv('AWS_ACCESS_KEY_ID'),
            "aws_secret_access_key": os.getenv('AWS_SECRET_ACCESS_KEY'),
            "region_name": os.getenv('AWS_REGION')
        }
        
        self.s3_client = boto3.client('s3', **aws_config)
        self.bedrock_client = boto3.client('bedrock-runtime', **aws_config)
        self.dynamodb = boto3.resource('dynamodb', **aws_config)

    def _sanitize_title(self, title: str) -> str:
        """Sanitize title for folder naming"""
        try:
            return re.sub(r'[^A-Za-z0-9_]+', '_', title.strip())
        except Exception as e:
            logger.error(f"Error sanitizing title '{title}': {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid title format")

    def _generate_folder_name(self, title: Optional[str] = None) -> str:
        """Generate folder name with timestamp"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            if title:
                clean_title = self._sanitize_title(title)
                return f"{timestamp}_{clean_title}"
            return timestamp
        except Exception as e:
            logger.error(f"Error generating folder name: {str(e)}")
            raise HTTPException(status_code=500, detail="Error generating folder name")

    # AGENT 1: S3 Storage Agent
    async def storage_agent(self, images: List[UploadFile], excel: Optional[UploadFile], 
                          folder_name: str) -> Dict[str, Any]:
        """Agent 1: Store all uploaded files into S3"""
        try:
            logger.info(f"Storage Agent: Processing files for folder {folder_name}")
            result = {
                "folder_name": folder_name,
                "images": [],
                "excel": None,
                "excel_content": None,  # Store Excel content for later analysis
                "image_contents": {}  # Store image contents for later analysis
            }
            
            # Store images
            if images:
                logger.info(f"Storage Agent: Processing {len(images)} images")
                for idx, image in enumerate(images):
                    try:
                        # Validate image file
                        if not image.content_type or not image.content_type.startswith('image/'):
                            logger.warning(f"Invalid image type: {image.content_type}")
                            continue
                        
                        # Read image content before uploading to preserve it for analysis
                        image_content = await image.read()
                        await image.seek(0)  # Reset for upload
                        
                        filename = image.filename or f"image_{idx}.jpg"
                        s3_url = await self.upload_file_to_s3(
                            image.file, folder_name, "images", filename
                        )
                        
                        result["images"].append({
                            "filename": filename,
                            "s3_url": s3_url
                        })
                        result["image_contents"][filename] = {
                            "content": image_content,
                            "content_type": image.content_type
                        }
                        logger.info(f"Storage Agent: Uploaded image {filename}")
                        
                    except Exception as e:
                        logger.error(f"Storage Agent: Error uploading image {idx}: {str(e)}")
                        continue
            
            # Store Excel file
            if excel:
                try:
                    logger.info("Storage Agent: Processing Excel file")
                    # Validate Excel file
                    if not excel.content_type or excel.content_type not in [
                        'application/vnd.ms-excel',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    ]:
                        logger.warning(f"Invalid Excel type: {excel.content_type}")
                    else:
                        # Read Excel content before uploading to preserve it for analysis
                        excel_content = await excel.read()
                        await excel.seek(0)  # Reset for upload
                        
                        filename = excel.filename or "data.xlsx"
                        s3_url = await self.upload_file_to_s3(
                            excel.file, folder_name, "excel", filename
                        )
                        
                        result["excel"] = {
                            "filename": filename,
                            "s3_url": s3_url
                        }
                        result["excel_content"] = excel_content  # Store content for analysis
                        logger.info(f"Storage Agent: Uploaded Excel file {filename}")
                        
                except Exception as e:
                    logger.error(f"Storage Agent: Error uploading Excel file: {str(e)}")
            
            logger.info(f"Storage Agent: Completed processing for folder {folder_name}")
            return result
            
        except Exception as e:
            logger.error(f"Storage Agent: Critical error: {str(e)}")
            raise HTTPException(status_code=500, detail="Storage agent failed")

    async def upload_file_to_s3(self, file, folder_name, subfolder, filename):
        try:
            key = f"{folder_name}/{subfolder}/{filename}"
            self.s3_client.upload_fileobj(file, os.getenv('S3_BUCKET_NAME'), key)
            return f"s3://{os.getenv('S3_BUCKET_NAME')}/{key}"
        except ClientError as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to storage"
            )
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during file upload"
            )

    # AGENT 2: Image Analysis Agent
    async def image_analysis_agent(self, storage_result: Dict[str, Any], 
                                 context: str = "") -> Dict[str, Any]:
        """Agent 2: Process images using AWS Bedrock"""
        try:
            stored_images = storage_result.get("images", [])
            image_contents = storage_result.get("image_contents", {})
            
            logger.info(f"Image Analysis Agent: Processing {len(stored_images)} images")
            image_analysis = []
            
            for storage_info in stored_images:
                try:
                    filename = storage_info["filename"]
                    
                    # Get stored image content
                    if filename not in image_contents:
                        logger.warning(f"No stored content found for image {filename}")
                        continue
                        
                    image_data = image_contents[filename]
                    
                    # Analyze image with Bedrock using stored content
                    prompt = f"Context: {context}\nPlease analyze this image and provide detailed insights."
                    analysis_result = await self._analyze_with_bedrock_content(
                        prompt, image_data["content"], image_data["content_type"]
                    )
                    
                    image_analysis.append({
                        "filename": storage_info["filename"],
                        "s3_url": storage_info["s3_url"],
                        "context": context,
                        "analysis_result": analysis_result
                    })
                    
                    logger.info(f"Image Analysis Agent: Completed analysis for {storage_info['filename']}")
                    
                except Exception as e:
                    logger.error(f"Image Analysis Agent: Error processing image {filename}: {str(e)}")
                    continue
            
            logger.info(f"Image Analysis Agent: Completed processing {len(image_analysis)} images")
            return {"image_analysis": image_analysis}
            
        except Exception as e:
            logger.error(f"Image Analysis Agent: Critical error: {str(e)}")
            raise HTTPException(status_code=500, detail="Image analysis agent failed")

    # AGENT 3: Excel Analysis Agent
    async def excel_analysis_agent(self, storage_result: Dict[str, Any], 
                                 context: str = "") -> Dict[str, Any]:
        """Agent 3: Excel validation and insights"""
        try:
            logger.info("Excel Analysis Agent: Processing Excel file")
            
            if not storage_result.get("excel") or not storage_result.get("excel_content"):
                logger.info("Excel Analysis Agent: No Excel file to process")
                return {"excel_analysis": None}
            
            # Use stored Excel content instead of reading from closed file
            excel_bytes = storage_result.get("excel_content")
            df = pd.read_excel(io.BytesIO(excel_bytes))
            
            # Validate and process Excel data
            insights = []
            excel_data_summary = []
            
            for idx, row in df.iterrows():
                try:
                    # Convert row to string representation
                    row_data = ", ".join([f"{col}: {val}" for col, val in row.items()])
                    excel_data_summary.append(row_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing row {idx}: {str(e)}")
                    continue
            
            # Prepare Bedrock input
            excel_summary = "; ".join(excel_data_summary[:10])  # Limit to first 10 rows
            prompt = f"""Context: {context}
Excel Data Summary: {excel_summary}
Column Headers: {', '.join(df.columns.tolist())}
Total Rows: {len(df)}

Please analyze this Excel data and provide insights including:
1. Data summary and patterns
2. Key metrics and statistics
3. Anomalies or notable observations
4. Recommendations based on the data"""

            analysis_result = await self._analyze_with_bedrock(prompt)
            
            # Process insights for each row (limited sample)
            for idx, row in df.head(5).iterrows():  # Process first 5 rows
                try:
                    row_summary = f"Row {idx}: " + ", ".join([f"{col}={val}" for col, val in row.items()])
                    insights.append({
                        "row_index": idx,
                        "summary": row_summary
                    })
                except Exception as e:
                    logger.warning(f"Error creating summary for row {idx}: {str(e)}")
            
            excel_analysis = {
                "s3_url": storage_result["excel"]["s3_url"],
                "context": context,
                "analysis_result": analysis_result,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": df.columns.tolist(),
                "insights": insights
            }
            
            logger.info("Excel Analysis Agent: Completed Excel analysis")
            return {"excel_analysis": excel_analysis}
            
        except Exception as e:
            logger.error(f"Excel Analysis Agent: Critical error: {str(e)}")
            raise HTTPException(status_code=500, detail="Excel analysis agent failed")

    # AGENT 4: DynamoDB Storage Agent
    async def dynamodb_storage_agent(self, user_id: str, title: str, folder_name: str,
                                   context: str, image_analysis: Dict[str, Any],
                                   excel_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 4: Store consolidated results in DynamoDB"""
        try:
            logger.info(f"DynamoDB Storage Agent: Storing data for user {user_id}")
            
            table = self.dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME'))
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            # Prepare DynamoDB item
            item = {
                "pk": f"USER#{user_id}",
                "sk": f"PROJECT#{folder_name}",
                "title": title,
                "folder_name": folder_name,
                "created_at": timestamp,
                "context": context
            }
            
            # Add image analysis if available
            if image_analysis and image_analysis.get("image_analysis"):
                item["images"] = image_analysis["image_analysis"]
            
            # Add Excel analysis if available
            if excel_analysis and excel_analysis.get("excel_analysis"):
                item["excel"] = excel_analysis["excel_analysis"]
            
            # Store in DynamoDB
            table.put_item(Item=item)
            
            logger.info(f"DynamoDB Storage Agent: Successfully stored data for project {folder_name}")
            return {
                "status": "success",
                "user_id": user_id,
                "project_key": f"USER#{user_id}#PROJECT#{folder_name}",
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"DynamoDB Storage Agent: Critical error: {str(e)}")
            raise HTTPException(status_code=500, detail="DynamoDB storage agent failed")

    async def _analyze_with_bedrock(self, content: str, image_file: UploadFile = None) -> str:
        """Internal method for Bedrock analysis"""
        try:
            if image_file:
                # Read and encode the image
                image_bytes = await image_file.read()
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                media_type = image_file.content_type

                # Construct message with image and text
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_b64
                                }
                            },
                            {
                                "type": "text",
                                "text": content
                            }
                        ]
                    }
                ]
            else:
                # Text-only message
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": content
                            }
                        ]
                    }
                ]

            # Format request for Claude-3
            request_body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": messages
            })

            # Invoke the model directly with ARN
            response = self.bedrock_client.invoke_model(
                modelId="arn:aws:bedrock:us-east-1:772986066238:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                body=request_body,
                contentType="application/json",
                accept="application/json"
            )

            # Parse the response
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ValidationException':
                logger.error(f"Bedrock validation error: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Bedrock configuration: {str(e)}"
                )
            elif "ModelNotReadyException" in str(e):
                logger.error(f"Model not ready: {str(e)}")
                raise HTTPException(
                    status_code=503,
                    detail="Model is currently not available. Please try again later."
                )
            else:
                logger.error(f"AWS Bedrock error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Error processing with AI model"
                )
        except Exception as e:
            logger.error(f"Unexpected error in _analyze_with_bedrock: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during analysis"
            )

    async def _analyze_with_bedrock_content(self, content: str, image_bytes: bytes, media_type: str) -> str:
        """Internal method for Bedrock analysis using binary content"""
        try:
            # Encode the image
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            # Construct message with image and text
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": content
                        }
                    ]
                }
            ]

            # Format request for Claude-3
            request_body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": messages
            })

            # Invoke the model directly with ARN
            response = self.bedrock_client.invoke_model(
                modelId="arn:aws:bedrock:us-east-1:772986066238:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                body=request_body,
                contentType="application/json",
                accept="application/json"
            )

            # Parse the response
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ValidationException':
                logger.error(f"Bedrock validation error: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Bedrock configuration: {str(e)}"
                )
            elif "ModelNotReadyException" in str(e):
                logger.error(f"Model not ready: {str(e)}")
                raise HTTPException(
                    status_code=503,
                    detail="Model is currently not available. Please try again later."
                )
            else:
                logger.error(f"AWS Bedrock error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Error processing with AI model"
                )
        except Exception as e:
            logger.error(f"Unexpected error in _analyze_with_bedrock_content: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during analysis"
            )

    # Main orchestrator method
    async def process_upload(self, user_id: str, title: Optional[str], images: List[UploadFile], 
                           excel: Optional[UploadFile], context: str = "") -> Dict[str, Any]:
        """Main method to orchestrate all 4 agents"""
        try:
            logger.info(f"Starting upload processing for user {user_id}")
            
            # Generate folder name
            folder_name = self._generate_folder_name(title)
            
            # Agent 1: Storage
            storage_result = await self.storage_agent(images, excel, folder_name)
            
            # Agent 2: Image Analysis
            image_analysis = {"image_analysis": []}
            if images:
                image_analysis = await self.image_analysis_agent(storage_result, context)
            
            # Agent 3: Excel Analysis
            excel_analysis = {"excel_analysis": None}
            if excel:
                excel_analysis = await self.excel_analysis_agent(storage_result, context)
            
            # Agent 4: DynamoDB Storage
            db_result = await self.dynamodb_storage_agent(
                user_id, title or "Untitled", folder_name, context, image_analysis, excel_analysis
            )
            
            # Prepare clean response (exclude binary content)
            clean_storage_details = {
                "folder_name": storage_result["folder_name"],
                "images": storage_result["images"],
                "excel": storage_result["excel"]
                # Exclude 'excel_content' and 'image_contents' as they contain binary data
            }
            
            response = {
                "status": "success",
                "folder_name": folder_name,
                "images_processed": len(image_analysis.get("image_analysis", [])),
                "excel_processed": excel_analysis.get("excel_analysis") is not None,
                "storage_details": clean_storage_details,
                "db_reference": db_result["project_key"]
            }
            
            logger.info(f"Successfully completed upload processing for user {user_id}")
            return response
            
        except HTTPException as e:
            logger.error(f"HTTP error in process_upload: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Critical error in process_upload: {str(e)}")
            raise HTTPException(status_code=500, detail="Upload processing failed")