from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ImageSummary(BaseModel):
    """Summary information for an image file"""
    filename: str = Field(..., description="Original filename of the image")
    s3_url: str = Field(..., description="S3 storage URL")
    has_analysis: bool = Field(..., description="Whether AI analysis was performed")

class ExcelSummary(BaseModel):
    """Summary information for an Excel file"""
    filename: str = Field(..., description="Original filename of the Excel file")
    s3_url: str = Field(..., description="S3 storage URL")
    row_count: int = Field(..., description="Number of rows in the Excel file")
    column_count: int = Field(..., description="Number of columns in the Excel file")
    columns: List[str] = Field(..., description="List of column names")
    has_analysis: bool = Field(..., description="Whether AI analysis was performed")

class ProjectSummary(BaseModel):
    """Summary information for a project"""
    project_id: str = Field(..., description="Unique project identifier")
    folder_name: str = Field(..., description="S3 folder name for the project")
    title: str = Field(..., description="Project title")
    created_at: str = Field(..., description="ISO timestamp of project creation")
    context: str = Field(..., description="User-provided context for the project")
    has_images: bool = Field(..., description="Whether project contains images")
    has_excel: bool = Field(..., description="Whether project contains Excel file")
    has_documents: bool = Field(..., description="Whether project contains document files")
    image_count: int = Field(..., description="Number of images in the project")
    document_count: int = Field(..., description="Number of document files in the project")
    excel_analyzed: bool = Field(..., description="Whether Excel analysis was completed")
    documents_analyzed: bool = Field(..., description="Whether document analysis was completed")

class UserProjectsResponse(BaseModel):
    """Response model for user projects endpoint"""
    user_id: str = Field(..., description="User identifier")
    total_projects: int = Field(..., description="Total number of projects for the user")
    projects: List[ProjectSummary] = Field(..., description="List of user projects")
    has_more: bool = Field(..., description="Whether there are more projects beyond the limit")
    limit: int = Field(..., description="Maximum number of projects returned")

class ProjectMetadata(BaseModel):
    """Metadata information for a project"""
    image_count: int = Field(..., description="Number of images in the project")
    document_count: int = Field(..., description="Number of document files in the project")
    has_excel: bool = Field(..., description="Whether project contains Excel file")
    has_documents: bool = Field(..., description="Whether project contains document files")
    total_files: int = Field(..., description="Total number of files in the project")

class ProjectDetailsResponse(BaseModel):
    """Response model for project details endpoint"""
    user_id: str = Field(..., description="User identifier")
    project_id: str = Field(..., description="Project identifier")
    folder_name: str = Field(..., description="S3 folder name")
    title: str = Field(..., description="Project title")
    created_at: str = Field(..., description="ISO timestamp of project creation")
    context: str = Field(..., description="User-provided context")
    images: List[Dict[str, Any]] = Field(..., description="Complete image analysis data")
    excel: Dict[str, Any] = Field(..., description="Complete Excel analysis data")
    documents: List[Dict[str, Any]] = Field(..., description="Complete document analysis data")
    metadata: ProjectMetadata = Field(..., description="Project metadata")

class UsersCountResponse(BaseModel):
    """Response model for users count endpoint"""
    total_unique_users: int = Field(..., description="Total number of unique users")
    user_ids: List[str] = Field(..., description="List of all user IDs")

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")