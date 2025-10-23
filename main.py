from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging
import os
from src.api.routes import router
from src.utils.logger import setup_logger
from src.utils.exceptions import ServiceException, handle_service_exception

# Setup logging
os.makedirs("logs", exist_ok=True)
logger = setup_logger("main", "logs/main.log")

# Create FastAPI app
app = FastAPI(
    title="AWS Image and Excel Analysis Service",
    description="Unified API for analyzing images and Excel files using AWS Bedrock",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Add test upload page route
# @app.get("/test")
# async def test_upload_page():
#     """Serve the test upload page"""
#     return FileResponse("test_upload.html")

# Global exception handlers
@app.exception_handler(ServiceException)
async def service_exception_handler(request, exc: ServiceException):
    """Handle custom service exceptions"""
    http_exc = handle_service_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred"
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "AWS Image and Excel Analysis Service",
        "version": "1.0.0",
        "status": "running",
        "description": "Unified API for analyzing images and Excel files using AWS Bedrock with user authentication",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/api/health",
            # Authentication endpoints
            "register": "/api/auth/register",
            "login": "/api/auth/login",
            "request_password_reset": "/api/auth/request-password-reset",
            "verify_password_reset": "/api/auth/verify-reset",
            # Project endpoints
            "upload": "/api/analyze/upload",
            "users_count": "/api/users/count",
            "user_projects": "/api/projects/{user_id}",
            "project_details": "/api/projects/{user_id}/{project_id}"
        },
        "features": [
            "User Authentication with Email & Password",
            "JWT Token-based Sessions",
            "Email OTP for Password Reset (AWS SES)",
            "4-Agent Architecture for file processing",
            "AWS Bedrock Claude-3 AI analysis",
            "S3 secure file storage",
            "DynamoDB single-table design",
            "Multi-file upload support",
            "Project search and filtering"
        ],
        "authentication": {
            "type": "JWT Bearer Token",
            "registration_required": True,
            "password_reset": "Email OTP (10 min validity)",
            "token_expiration": "24 hours (configurable)"
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting AWS Image and Excel Analysis Service")
    logger.info("Service initialized successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down AWS Image and Excel Analysis Service")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server with uvicorn")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )