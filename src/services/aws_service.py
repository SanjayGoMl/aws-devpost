import os
import json
import re
import boto3
import boto3.dynamodb.conditions
import logging
import base64
import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile
from botocore.exceptions import ClientError

# Configure logging with fallback for missing logs directory
def setup_logging():
    """Setup logging with graceful fallback if logs directory doesn't exist"""
    handlers = []
    
    # Try to add file handler, fallback to console-only if logs dir doesn't exist
    try:
        os.makedirs('logs', exist_ok=True)
        handlers.append(logging.FileHandler('logs/aws_service.log'))
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not create log file, using console only: {e}")
    
    # Always add console handler
    handlers.append(logging.StreamHandler())
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

setup_logging()
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
                          documents: List[UploadFile], folder_name: str) -> Dict[str, Any]:
        """Agent 1: Store all uploaded files into S3"""
        try:
            logger.info(f"Storage Agent: Processing files for folder {folder_name}")
            result = {
                "folder_name": folder_name,
                "images": [],
                "excel": None,
                "documents": [],
                "excel_content": None,  # Store Excel content for later analysis
                "image_contents": {},  # Store image contents for later analysis
                "document_contents": {}  # Store document contents for later analysis
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
            
            # Store Documents
            if documents:
                logger.info(f"Storage Agent: Processing {len(documents)} documents")
                for idx, document in enumerate(documents):
                    try:
                        # Validate document file
                        valid_extensions = ['.txt', '.pdf']
                        if not document.filename or not any(document.filename.lower().endswith(ext) for ext in valid_extensions):
                            logger.warning(f"Invalid document type: {document.filename}")
                            continue
                        
                        # Read document content before uploading to preserve it for analysis
                        document_content = await document.read()
                        await document.seek(0)  # Reset for upload
                        
                        filename = document.filename or f"document_{idx}.txt"
                        s3_url = await self.upload_file_to_s3(
                            document.file, folder_name, "documents", filename
                        )
                        
                        result["documents"].append({
                            "filename": filename,
                            "s3_url": s3_url
                        })
                        result["document_contents"][filename] = {
                            "content": document_content,
                            "content_type": document.content_type
                        }
                        logger.info(f"Storage Agent: Uploaded document {filename}")
                        
                    except Exception as e:
                        logger.error(f"Storage Agent: Error uploading document {idx}: {str(e)}")
                        continue
            
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
                                 context: str = "", image_descriptions: List[str] = None) -> Dict[str, Any]:
        """Agent 2: Process images using AWS Bedrock"""
        try:
            stored_images = storage_result.get("images", [])
            image_contents = storage_result.get("image_contents", {})
            
            # Handle None case for image_descriptions
            if image_descriptions is None:
                image_descriptions = []
            
            logger.info(f"Image Analysis Agent: Processing {len(stored_images)} images with {len(image_descriptions)} descriptions")
            image_analysis = []
            
            for idx, storage_info in enumerate(stored_images):
                try:
                    filename = storage_info["filename"]
                    
                    # Get stored image content
                    if filename not in image_contents:
                        logger.warning(f"No stored content found for image {filename}")
                        continue
                        
                    image_data = image_contents[filename]
                    
                    # Get description for this specific image (by index)
                    specific_description = image_descriptions[idx] if idx < len(image_descriptions) else ""
                    
                    # Analyze image with Bedrock using stored content
                    prompt_parts = []
                    if context:
                        prompt_parts.append(f"Context: {context}")
                    if specific_description:
                        prompt_parts.append(f"Image Description: {specific_description}")
                    prompt_parts.append("Please analyze this image and provide detailed insights.")
                    
                    prompt = "\n".join(prompt_parts)
                    analysis_result = await self._analyze_with_bedrock_content(
                        prompt, image_data["content"], image_data["content_type"]
                    )
                    
                    image_analysis.append({
                        "filename": storage_info["filename"],
                        "s3_url": storage_info["s3_url"],
                        "context": context,
                        "image_description": specific_description,
                        "analysis_result": analysis_result,
                        "upload_index": idx  # Track which image this was in the upload order
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

    # AGENT 3.5: Document Analysis Agent
    async def document_analysis_agent(self, storage_result: Dict[str, Any], 
                                    context: str = "") -> Dict[str, Any]:
        """Agent 3.5: Process and analyze document files using Bedrock"""
        try:
            stored_documents = storage_result.get("documents", [])
            document_contents = storage_result.get("document_contents", {})
            
            logger.info(f"Document Analysis Agent: Processing {len(stored_documents)} documents")
            document_analysis = []
            
            for storage_info in stored_documents:
                try:
                    filename = storage_info["filename"]
                    
                    # Get stored document content
                    if filename not in document_contents:
                        logger.warning(f"No stored content found for document {filename}")
                        continue
                        
                    document_data = document_contents[filename]
                    
                    # Process document content based on file type
                    if filename.lower().endswith('.txt'):
                        # Process text file
                        text_content = document_data["content"].decode('utf-8')
                        
                        prompt = f"""Context: {context}
Document Type: Text File
Document Content: {text_content[:2000]}...  # Limit content for processing

Please analyze this text document and provide insights including:
1. Document summary and main topics
2. Key information and themes
3. Important data or findings
4. Recommendations based on the content"""

                        analysis_result = await self._analyze_with_bedrock(prompt)
                        
                    elif filename.lower().endswith('.pdf'):
                        # For PDF files, we'll provide a placeholder analysis
                        # In a real implementation, you'd use a PDF parsing library like PyPDF2 or pdfplumber
                        analysis_result = f"PDF document '{filename}' uploaded successfully. PDF content analysis requires additional processing libraries."
                        
                    document_analysis.append({
                        "filename": storage_info["filename"],
                        "s3_url": storage_info["s3_url"],
                        "context": context,
                        "document_type": "PDF" if filename.lower().endswith('.pdf') else "Text",
                        "analysis_result": analysis_result
                    })
                    
                    logger.info(f"Document Analysis Agent: Completed analysis for {storage_info['filename']}")
                    
                except Exception as e:
                    logger.error(f"Document Analysis Agent: Error processing document {filename}: {str(e)}")
                    continue
            
            logger.info(f"Document Analysis Agent: Completed processing {len(document_analysis)} documents")
            return {"document_analysis": document_analysis}
            
        except Exception as e:
            logger.error(f"Document Analysis Agent: Critical error: {str(e)}")
            raise HTTPException(status_code=500, detail="Document analysis agent failed")

    # AGENT 4: DynamoDB Storage Agent
    async def dynamodb_storage_agent(self, user_id: str, title: str, folder_name: str,
                                   context: str, image_analysis: Dict[str, Any],
                                   excel_analysis: Dict[str, Any], 
                                   document_analysis: Dict[str, Any]) -> Dict[str, Any]:
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
            
            # Add document analysis if available
            if document_analysis and document_analysis.get("document_analysis"):
                item["documents"] = document_analysis["document_analysis"]
            
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

    # GET PROJECTS METHOD
    async def get_user_projects(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """Retrieve all projects for a specific user from DynamoDB"""
        try:
            logger.info(f"Retrieving projects for user {user_id}")
            
            table = self.dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME'))
            
            # Query DynamoDB for all projects belonging to the user
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('pk').eq(f'USER#{user_id}'),
                ScanIndexForward=False,  # Sort by sort key in descending order (newest first)
                Limit=limit
            )
            
            projects = []
            for item in response.get('Items', []):
                # Parse the project data based on actual DynamoDB structure
                project_id = item.get('sk', '').replace('PROJECT#', '')
                
                project = {
                    "project_id": project_id,
                    "folder_name": project_id,  # Use project_id as folder_name if not separate
                    "title": item.get('title', project_id),  # Use project_id as title if no title
                    "created_at": item.get('created_at', ''),
                    "context": item.get('context', ''),
                    "has_images": bool(item.get('images')),
                    "has_excel": bool(item.get('excel')),
                    "has_documents": bool(item.get('documents')),
                }
                
                # Count images if they exist
                if item.get('images') and isinstance(item.get('images'), list):
                    project["image_count"] = len(item.get('images'))
                else:
                    project["image_count"] = 0
                
                # Count documents if they exist
                if item.get('documents') and isinstance(item.get('documents'), list):
                    project["document_count"] = len(item.get('documents'))
                else:
                    project["document_count"] = 0
                
                # Check if analyses exist
                project["excel_analyzed"] = bool(item.get('excel'))
                project["documents_analyzed"] = bool(item.get('documents'))
                
                projects.append(project)
            
            # Get total count for pagination info
            total_projects = len(projects)
            has_more = len(response.get('Items', [])) == limit
            
            result = {
                "user_id": user_id,
                "total_projects": total_projects,
                "projects": projects,
                "has_more": has_more,
                "limit": limit
            }
            
            logger.info(f"Successfully retrieved {total_projects} projects for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving projects for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve projects for user {user_id}"
            )

    async def get_project_details(self, user_id: str, project_id: str) -> Dict[str, Any]:
        """Retrieve detailed information for a specific project"""
        try:
            logger.info(f"Retrieving project details for user {user_id}, project {project_id}")
            
            table = self.dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME'))
            
            # Get specific project
            response = table.get_item(
                Key={
                    'pk': f'USER#{user_id}',
                    'sk': f'PROJECT#{project_id}'
                }
            )
            
            if 'Item' not in response:
                raise HTTPException(
                    status_code=404,
                    detail=f"Project {project_id} not found for user {user_id}"
                )
            
            item = response['Item']
            
            # Format detailed project information based on actual DynamoDB structure
            project_details = {
                "user_id": user_id,
                "project_id": project_id,
                "folder_name": project_id,  # Use project_id as folder name
                "title": item.get('title', project_id),  # Use project_id as title if no title
                "created_at": item.get('created_at', ''),
                "context": item.get('context', ''),
                "images": item.get('images', []),  # Full images array
                "excel": item.get('excel', {}),    # Full excel object
                "documents": item.get('documents', []),  # Full documents array
                "metadata": {
                    "image_count": len(item.get('images', [])) if item.get('images') else 0,
                    "document_count": len(item.get('documents', [])) if item.get('documents') else 0,
                    "has_excel": bool(item.get('excel')),
                    "has_documents": bool(item.get('documents')),
                    "total_files": (len(item.get('images', [])) if item.get('images') else 0) + 
                                  (1 if item.get('excel') else 0) + 
                                  (len(item.get('documents', [])) if item.get('documents') else 0)
                }
            }
            
            logger.info(f"Successfully retrieved project details for {project_id}")
            return project_details
            
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error retrieving project details: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve project details for {project_id}"
            )

    async def get_total_users(self) -> Dict[str, Any]:
        """Get total number of unique users (PKs) in the system"""
        try:
            logger.info("Retrieving total unique users count")
            
            table = self.dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME'))
            
            # Scan the table to get all unique PKs
            unique_users = set()
            
            # Use scan with pagination to get all items
            scan_kwargs = {
                'ProjectionExpression': 'pk'
            }
            
            done = False
            start_key = None
            
            while not done:
                if start_key:
                    scan_kwargs['ExclusiveStartKey'] = start_key
                
                response = table.scan(**scan_kwargs)
                
                # Extract unique user IDs
                for item in response.get('Items', []):
                    pk = item.get('pk', '')
                    if pk.startswith('USER#'):
                        user_id = pk.replace('USER#', '')
                        unique_users.add(user_id)
                
                start_key = response.get('LastEvaluatedKey', None)
                done = start_key is None
            
            result = {
                "total_unique_users": len(unique_users),
                "user_ids": sorted(list(unique_users))
            }
            
            logger.info(f"Found {len(unique_users)} unique users")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving total users: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve total users count"
            )

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
                           excel: Optional[UploadFile], documents: List[UploadFile] = None, 
                           context: str = "", image_descriptions: List[str] = None) -> Dict[str, Any]:
        """Main method to orchestrate all 4 agents"""
        try:
            logger.info(f"Starting upload processing for user {user_id}")
            
            # Generate folder name
            folder_name = self._generate_folder_name(title)
            
            # Agent 1: Storage
            storage_result = await self.storage_agent(images, excel, documents or [], folder_name)
            
            # Agent 2: Image Analysis
            image_analysis = {"image_analysis": []}
            if images:
                image_analysis = await self.image_analysis_agent(storage_result, context, image_descriptions or [])
            
            # Agent 3: Excel Analysis
            excel_analysis = {"excel_analysis": None}
            if excel:
                excel_analysis = await self.excel_analysis_agent(storage_result, context)
            
            # Agent 3.5: Document Analysis
            document_analysis = {"document_analysis": []}
            if documents:
                document_analysis = await self.document_analysis_agent(storage_result, context)
            
            # Agent 4: DynamoDB Storage
            db_result = await self.dynamodb_storage_agent(
                user_id, title or "Untitled", folder_name, context, 
                image_analysis, excel_analysis, document_analysis
            )
            
            # Prepare clean response (exclude binary content)
            clean_storage_details = {
                "folder_name": storage_result["folder_name"],
                "images": storage_result["images"],
                "excel": storage_result["excel"],
                "documents": storage_result["documents"]
                # Exclude binary content fields
            }
            
            response = {
                "status": "success",
                "folder_name": folder_name,
                "images_processed": len(image_analysis.get("image_analysis", [])),
                "excel_processed": excel_analysis.get("excel_analysis") is not None,
                "documents_processed": len(document_analysis.get("document_analysis", [])),
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