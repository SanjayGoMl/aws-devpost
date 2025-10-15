import os
from datetime import datetime
from typing import Dict, Optional
import boto3
from botocore.exceptions import ClientError
from ..utils.logger import setup_logger
from ..utils.exceptions import DynamoDBError

logger = setup_logger("dynamodb_agent")

class DynamoDBAgent:
    def __init__(self):
        # Validate required environment variables
        required_vars = {
            'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
            'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'AWS_REGION': os.getenv('AWS_REGION'),
            'DYNAMODB_TABLE_NAME': os.getenv('DYNAMODB_TABLE_NAME')
        }

        # Check for missing environment variables
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            self.dynamodb = boto3.resource('dynamodb',
                aws_access_key_id=required_vars['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=required_vars['AWS_SECRET_ACCESS_KEY'],
                region_name=required_vars['AWS_REGION']
            )
            
            # Initialize table
            self.table = self.dynamodb.Table(required_vars['DYNAMODB_TABLE_NAME'])
            
            # Verify table exists by making a simple call
            self.table.table_status
            logger.info(f"Successfully connected to DynamoDB table: {required_vars['DYNAMODB_TABLE_NAME']}")
            
        except self.dynamodb.meta.client.exceptions.ResourceNotFoundException:
            error_msg = f"DynamoDB table {required_vars['DYNAMODB_TABLE_NAME']} does not exist"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error initializing DynamoDB connection: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    async def store_analysis(
        self,
        user_id: str,
        folder_name: str,
        title: Optional[str],
        context: str,
        image_analysis: Optional[Dict] = None,
        excel_analysis: Optional[Dict] = None
    ) -> Dict:
        try:
            timestamp = datetime.utcnow().isoformat()
            
            # Prepare item for DynamoDB
            item = {
                "pk": f"USER#{user_id}",
                "sk": f"PROJECT#{folder_name}",
                "title": title or folder_name,
                "folder_name": folder_name,
                "created_at": timestamp,
                "context": context
            }

            # Add image analysis if present
            if image_analysis:
                item["images"] = image_analysis.get("image_analysis", [])

            # Add excel analysis if present
            if excel_analysis:
                item["excel"] = excel_analysis.get("excel_analysis", {})

            # Store in DynamoDB
            try:
                self.table.put_item(Item=item)
                logger.info(f"Successfully stored analysis for folder: {folder_name}")
                
                return {
                    "status": "success",
                    "folder_name": folder_name,
                    "images_processed": len(item.get("images", [])),
                    "excel_processed": "excel" in item
                }

            except ClientError as e:
                error_msg = f"DynamoDB error: {str(e)}"
                logger.error(error_msg)
                raise DynamoDBError(error_msg)

        except Exception as e:
            logger.error(f"Error in store_analysis: {str(e)}")
            raise DynamoDBError(f"Failed to store analysis: {str(e)}")