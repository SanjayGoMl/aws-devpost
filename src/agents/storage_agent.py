from datetime import datetime
import os
from typing import List, Optional, Dict
from fastapi import UploadFile
from ..utils.logger import setup_logger
from ..utils.exceptions import S3UploadError
import boto3
from botocore.exceptions import ClientError

logger = setup_logger("storage_agent")

class StorageAgent:
    def __init__(self):
        self.s3_client = boto3.client('s3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')

    def _generate_folder_name(self, title: Optional[str] = None) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if title:
            sanitized_title = "".join(c if c.isalnum() else "_" for c in title)
            return f"{timestamp}_{sanitized_title}"
        return timestamp

    async def store_files(
        self,
        images: Optional[List[UploadFile]] = None,
        excel: Optional[UploadFile] = None,
        title: Optional[str] = None
    ) -> Dict:
        try:
            folder_name = self._generate_folder_name(title)
            result = {
                "folder_name": folder_name,
                "images": [],
                "excel": None
            }

            # Store images if provided
            if images:
                for idx, image in enumerate(images):
                    try:
                        key = f"{folder_name}/images/{idx}_{image.filename}"
                        await self._upload_file(image, key)
                        result["images"].append({
                            "filename": image.filename,
                            "s3_url": f"s3://{self.bucket_name}/{key}"
                        })
                        logger.info(f"Successfully uploaded image: {image.filename}")
                    except Exception as e:
                        logger.error(f"Error uploading image {image.filename}: {str(e)}")
                        raise S3UploadError(f"Failed to upload image {image.filename}")

            # Store excel if provided
            if excel:
                try:
                    key = f"{folder_name}/excel/{excel.filename}"
                    await self._upload_file(excel, key)
                    result["excel"] = {
                        "filename": excel.filename,
                        "s3_url": f"s3://{self.bucket_name}/{key}"
                    }
                    logger.info(f"Successfully uploaded excel: {excel.filename}")
                except Exception as e:
                    logger.error(f"Error uploading excel {excel.filename}: {str(e)}")
                    raise S3UploadError(f"Failed to upload excel file {excel.filename}")

            return result

        except Exception as e:
            logger.error(f"Error in store_files: {str(e)}")
            raise S3UploadError(str(e))

    async def _upload_file(self, file: UploadFile, key: str):
        try:
            content = await file.read()
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content
            )
            await file.seek(0)  # Reset file pointer for potential reuse
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"AWS S3 error ({error_code}): {str(e)}")
            raise S3UploadError(f"S3 upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during file upload: {str(e)}")
            raise S3UploadError("Unexpected error during file upload")