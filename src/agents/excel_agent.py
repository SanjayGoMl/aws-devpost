import os
import json
import pandas as pd
from typing import Dict
from fastapi import UploadFile
import boto3
from botocore.exceptions import ClientError
from ..utils.logger import setup_logger
from ..utils.exceptions import ExcelProcessingError, BedrockError

logger = setup_logger("excel_agent")

class ExcelAnalysisAgent:
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )

    async def analyze_excel(
        self,
        excel_info: Dict,
        context: str,
        file: UploadFile
    ) -> Dict:
        try:
            # Read Excel file
            content = await file.read()
            df = pd.read_excel(content)
            
            # Basic validation
            if df.empty:
                raise ExcelProcessingError("Excel file is empty")

            # Convert DataFrame to structured text
            rows_text = []
            for idx, row in df.iterrows():
                row_text = ", ".join([f"{col}: {val}" for col, val in row.items()])
                rows_text.append(f"Row {idx + 1}: {row_text}")

            excel_content = "\n".join(rows_text)

            # Prepare prompt for Bedrock
            prompt = f"""Context: {context}

Excel Data:
{excel_content}

Please analyze this data and provide:
1. Key insights and patterns
2. Anomalies or unusual data points
3. Summary statistics
4. Recommendations based on the data"""

            # Prepare request for Bedrock
            request_body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            })

            try:
                # Call Bedrock
                response = self.bedrock_client.invoke_model(
                    modelId="arn:aws:bedrock:us-east-1:772986066238:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                    body=request_body,
                    contentType="application/json",
                    accept="application/json"
                )

                # Parse response
                response_body = json.loads(response['body'].read())
                analysis = response_body['content'][0]['text']

                # Process row-by-row insights
                insights = []
                for idx, row in df.iterrows():
                    insights.append({
                        "row_index": idx,
                        "summary": f"Row {idx + 1}: {', '.join([f'{k}={v}' for k, v in row.items()])}"
                    })

                logger.info(f"Successfully analyzed excel file: {excel_info['filename']}")

                return {
                    "excel_analysis": {
                        **excel_info,
                        "context": context,
                        "insights": insights,
                        "analysis": analysis
                    }
                }

            except ClientError as e:
                error_msg = f"Bedrock error: {str(e)}"
                logger.error(error_msg)
                raise BedrockError(error_msg)

        except pd.errors.EmptyDataError:
            logger.error("Excel file is empty")
            raise ExcelProcessingError("Excel file is empty")
        except pd.errors.ParserError as e:
            logger.error(f"Excel parsing error: {str(e)}")
            raise ExcelProcessingError(f"Failed to parse Excel file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in analyze_excel: {str(e)}")
            raise ExcelProcessingError(f"Failed to process Excel file: {str(e)}")

        finally:
            # Reset file pointer
            await file.seek(0)