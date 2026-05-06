"""File upload endpoints for CV management."""

import os
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from src.models import CVUploadResponse, Profile
from src.parse_cv import parse_cv as parse_cv_pipeline

router = APIRouter(prefix="/upload", tags=["upload"])


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "temp")


@router.post("/cv")
async def upload_cv(
    file: UploadFile = File(...),
    auto_parse: bool = True,
) -> CVUploadResponse:
    """Upload a CV file and optionally extract profile.

    Args:
        file: PDF file to upload
        auto_parse: If True, immediately parse CV and extract profile

    Returns:
        CVUploadResponse with upload status and optionally extracted profile
    """
    # Validate file type
    if file.content_type not in ["application/pdf", "text/plain"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save uploaded file
    try:
        file_path = os.path.join(UPLOAD_DIR, "uploaded_cv.pdf")
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    profile: Optional[Profile] = None

    # Parse CV if requested
    if auto_parse:
        try:
            # Temporarily override CV_PATH
            import config
            original_cv_path = config.CV_PATH
            config.CV_PATH = file_path

            profile_dict = parse_cv_pipeline(cv_path=file_path)
            profile = Profile(**profile_dict)

            config.CV_PATH = original_cv_path
        except Exception as e:
            # Log error but don't fail - upload succeeded
            print(f"[upload] CV parsing failed: {e}")
            return CVUploadResponse(
                success=True,
                message=f"CV uploaded but parsing failed: {str(e)}",
                cv_path=file_path,
                profile=None,
            )

    return CVUploadResponse(
        success=True,
        message="CV uploaded successfully",
        cv_path=file_path,
        profile=profile,
    )


@router.get("/status/{upload_id}")
async def get_upload_status(upload_id: str):
    """Get status of an upload operation."""
    # Simple implementation - in production, track uploads with IDs
    return {"upload_id": upload_id, "status": "completed"}

