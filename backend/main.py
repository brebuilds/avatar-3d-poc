"""
FastAPI backend for 3D Avatar Generator.
Provides REST API for avatar processing pipeline.
"""
import os
import uuid
import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline import AvatarPipeline
from utils.validators import validate_image_file, sanitize_filename


# Initialize FastAPI app
app = FastAPI(
    title="3D Avatar Generator API",
    description="Convert photos to 3D printable Pixar-style avatars",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OUTPUT_DIR = Path("output")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

# Job storage (in-memory for POC - use database in production)
jobs: Dict[str, Dict[str, Any]] = {}
job_lock = threading.Lock()


# Pydantic models
class JobStatus(BaseModel):
    """Job status response model."""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    current_step: Optional[str] = None
    output_files: Optional[Dict[str, str]] = None
    error: Optional[str] = None


# Initialize pipeline
pipeline = AvatarPipeline(
    output_dir=OUTPUT_DIR,
    target_height_mm=float(os.getenv("DEFAULT_TARGET_HEIGHT", "80")),
    printer_profile=os.getenv("DEFAULT_PRINTER_PROFILE", "ender3v2")
)


def update_job_status(job_id: str, step: str, data: dict):
    """Update job status in storage."""
    with job_lock:
        if job_id in jobs:
            jobs[job_id]["current_step"] = step
            jobs[job_id]["last_update"] = data


def process_avatar_background(job_id: str, input_path: Path):
    """Background task to process avatar."""
    try:
        # Update status
        with job_lock:
            jobs[job_id]["status"] = "processing"

        # Process avatar
        result = pipeline.process_avatar(
            input_path,
            job_id,
            status_callback=lambda step, data: update_job_status(job_id, step, data)
        )

        # Update final status
        with job_lock:
            if result["success"]:
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["result"] = result
                jobs[job_id]["output_files"] = result["output_files"]
            else:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = result.get("error", "Unknown error")

    except Exception as e:
        with job_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "3D Avatar Generator API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.post("/upload")
async def upload_photo(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a photo and start avatar generation.

    Returns:
        Job ID and initial status
    """
    # Generate job ID
    job_id = str(uuid.uuid4())

    # Validate file size
    file_size = 0
    content = await file.read()
    file_size = len(content) / (1024 * 1024)  # MB

    if file_size > MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file_size:.1f}MB (max {MAX_UPLOAD_SIZE_MB}MB)"
        )

    # Save uploaded file
    filename = sanitize_filename(file.filename)
    upload_path = OUTPUT_DIR / "uploads" / f"{job_id}_{filename}"

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "uploads").mkdir(parents=True, exist_ok=True)

    try:
        with open(upload_path, "wb") as f:
            f.write(content)

        # Verify file was written
        if not upload_path.exists():
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")

        # Validate image
        is_valid, message = validate_image_file(upload_path, check_size=False)
        if not is_valid:
            upload_path.unlink()  # Delete invalid file
            raise HTTPException(status_code=400, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

    # Create job record
    with job_lock:
        jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "upload_path": str(upload_path),
            "filename": filename,
            "created_at": str(Path(upload_path).stat().st_mtime)
        }

    # Start background processing
    background_tasks.add_task(process_avatar_background, job_id, upload_path)

    return {
        "job_id": job_id,
        "message": "Photo uploaded successfully. Processing started.",
        "status": "pending"
    }


@app.get("/status/{job_id}")
async def get_status(job_id: str) -> JobStatus:
    """
    Get processing status for a job.

    Args:
        job_id: Job identifier

    Returns:
        Job status with progress information
    """
    with job_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        job = jobs[job_id]

    status = job["status"]
    current_step = job.get("current_step")
    last_update = job.get("last_update", {})

    # Calculate progress
    progress_map = {
        "pending": 0,
        "face_detection": 10,
        "cartoonization": 30,
        "3d_generation": 60,
        "optimization": 85,
        "completed": 100,
        "failed": 0
    }

    progress = progress_map.get(current_step, progress_map.get(status, 0))
    if status == "completed":
        progress = 100

    return JobStatus(
        job_id=job_id,
        status=status,
        progress=progress,
        message=last_update.get("message", f"Status: {status}"),
        current_step=current_step,
        output_files=job.get("output_files"),
        error=job.get("error")
    )


@app.get("/preview/{job_id}")
async def get_preview(job_id: str):
    """
    Get GLB model file for 3D preview.

    Args:
        job_id: Job identifier

    Returns:
        GLB file
    """
    with job_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed yet (status: {job['status']})"
        )

    glb_path = Path(job["output_files"]["model_3d"])
    if not glb_path.exists():
        raise HTTPException(status_code=404, detail="GLB file not found")

    return FileResponse(
        glb_path,
        media_type="model/gltf-binary",
        filename=f"avatar_{job_id}.glb"
    )


@app.get("/download/{job_id}/stl")
async def download_stl(job_id: str):
    """
    Download optimized STL file for printing.

    Args:
        job_id: Job identifier

    Returns:
        STL file
    """
    with job_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed yet (status: {job['status']})"
        )

    stl_path = Path(job["output_files"]["stl"])
    if not stl_path.exists():
        raise HTTPException(status_code=404, detail="STL file not found")

    return FileResponse(
        stl_path,
        media_type="application/sla",
        filename=f"avatar_{job_id}.stl"
    )


@app.get("/download/{job_id}/cartoon")
async def download_cartoon(job_id: str):
    """
    Download cartoonized image.

    Args:
        job_id: Job identifier

    Returns:
        PNG image file
    """
    with job_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed yet (status: {job['status']})"
        )

    cartoon_path = Path(job["output_files"]["cartoon"])
    if not cartoon_path.exists():
        raise HTTPException(status_code=404, detail="Cartoon image not found")

    return FileResponse(
        cartoon_path,
        media_type="image/png",
        filename=f"cartoon_{job_id}.png"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
