import os
import json
import base64
from typing import List, Dict
from fastapi import UploadFile
import boto3
from botocore.exceptions import ClientError
from ..utils.logger import setup_logger
from ..utils.exceptions import BedrockError

logger = setup_logger("image_agent")

class ImageAnalysisAgent:
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )

    async def analyze_images(
        self,
        images: List[Dict],
        context: str,
        files: List[UploadFile]
    ) -> List[Dict]:
        try:
            results = []
            
            for idx, (image_info, file) in enumerate(zip(images, files)):
                try:
                    # Read and encode image
                    image_bytes = await file.read()
                    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                    
                    # Create message for Bedrock
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": file.content_type,
                                        "data": image_b64
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": f"{context}\nPlease analyze this image in detail."
                                }
                            ]
                        }
                    ]

                    # Prepare request body
                    request_body = json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 300,
                        "messages": messages
                    })

                    # Call Bedrock
                    response = self.bedrock_client.invoke_model(
                        modelId="arn:aws:bedrock:us-east-1:772986066238:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                        body=request_body,
                        contentType="application/json",
                        accept="application/json"
                    )

                    # Parse response
                    response_body = json.loads(response['body'].read())
                    analysis_result = response_body['content'][0]['text']

                    # Reset file pointer
                    await file.seek(0)

                    # Add to results
                    results.append({
                        **image_info,
                        "context": context,
                        "analysis_result": analysis_result
                    })

                    logger.info(f"Successfully analyzed image: {image_info['filename']}")

                except ClientError as e:
                    error_msg = f"Bedrock error analyzing image {image_info['filename']}: {str(e)}"
                    logger.error(error_msg)
                    results.append({
                        **image_info,
                        "context": context,
                        "analysis_result": "Error: Failed to analyze image",
                        "error": error_msg
                    })
                except Exception as e:
                    error_msg = f"Unexpected error analyzing image {image_info['filename']}: {str(e)}"
                    logger.error(error_msg)
                    results.append({
                        **image_info,
                        "context": context,
                        "analysis_result": "Error: Internal processing error",
                        "error": error_msg
                    })

            return {"image_analysis": results}

        except Exception as e:
            logger.error(f"Error in analyze_images: {str(e)}")
            raise BedrockError(f"Failed to analyze images: {str(e)}")