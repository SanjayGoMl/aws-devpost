"""
Custom exceptions for the AWS Image and Excel Analysis Service
"""

from fastapi import HTTPException
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ServiceException(Exception):
    """Base exception for service-related errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationException(ServiceException):
    """Exception for input validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR", details)

class StorageException(ServiceException):
    """Exception for S3 storage errors"""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.operation = operation
        super().__init__(message, "STORAGE_ERROR", details)

class AnalysisException(ServiceException):
    """Exception for Bedrock analysis errors"""
    
    def __init__(self, message: str, model_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.model_id = model_id
        super().__init__(message, "ANALYSIS_ERROR", details)

class DatabaseException(ServiceException):
    """Exception for DynamoDB errors"""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.operation = operation
        super().__init__(message, "DATABASE_ERROR", details)

class FileProcessingException(ServiceException):
    """Exception for file processing errors"""
    
    def __init__(self, message: str, file_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.file_type = file_type
        super().__init__(message, "FILE_PROCESSING_ERROR", details)

class AgentException(ServiceException):
    """Exception for agent-specific errors"""
    
    def __init__(self, message: str, agent_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.agent_name = agent_name
        super().__init__(message, "AGENT_ERROR", details)

def handle_service_exception(exc: ServiceException) -> HTTPException:
    """Convert service exceptions to HTTP exceptions"""
    
    status_code_map = {
        "VALIDATION_ERROR": 400,
        "STORAGE_ERROR": 500,
        "ANALYSIS_ERROR": 503,
        "DATABASE_ERROR": 500,
        "FILE_PROCESSING_ERROR": 400,
        "AGENT_ERROR": 500
    }
    
    status_code = status_code_map.get(exc.error_code, 500)
    
    logger.error(f"{exc.error_code}: {exc.message}", extra={
        "error_code": exc.error_code,
        "details": exc.details
    })
    
    return HTTPException(
        status_code=status_code,
        detail={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )

def handle_generic_exception(exc: Exception, context: str = "") -> HTTPException:
    """Handle generic exceptions and convert to HTTP exceptions"""
    
    error_message = f"Internal server error: {str(exc)}"
    if context:
        error_message = f"{context}: {error_message}"
    
    logger.error(error_message, exc_info=True)
    
    return HTTPException(
        status_code=500,
        detail={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "context": context
        }
    )

def safe_operation(operation_name: str):
    """Decorator to safely execute operations with proper exception handling"""
    
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ServiceException as e:
                raise handle_service_exception(e)
            except Exception as e:
                raise handle_generic_exception(e, operation_name)
        
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ServiceException as e:
                raise handle_service_exception(e)
            except Exception as e:
                raise handle_generic_exception(e, operation_name)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class ExceptionContext:
    """Context manager for handling exceptions in specific contexts"""
    
    def __init__(self, context: str, logger: Optional[logging.Logger] = None):
        self.context = context
        self.logger = logger or logging.getLogger(__name__)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            if isinstance(exc_val, ServiceException):
                self.logger.error(f"{self.context} - Service Exception: {exc_val.message}")
                return False  # Re-raise the exception
            else:
                self.logger.error(f"{self.context} - Unexpected error: {str(exc_val)}", exc_info=True)
                return False  # Re-raise the exception
        return False
