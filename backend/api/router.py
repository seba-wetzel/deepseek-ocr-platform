from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Body
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import shutil
import os
import uuid
import logging
import json
import asyncio
from backend.services.ocr_service import process_pdf_background
from backend.database import (
    init_db, create_job, get_job, get_all_jobs, cancel_job, delete_job,
    get_prompts, get_prompt, create_prompt, update_prompt
)

router = APIRouter()

UPLOAD_DIR = "data/uploads"
PROCESSED_DIR = "data/processed"
logger = logging.getLogger(__name__)

# Initialize DB on import
init_db()

class PromptRequest(BaseModel):
    name: str
    content: str
    description: Optional[str] = ""

@router.get("/prompts")
async def list_prompts_endpoint():
    return get_prompts()

@router.post("/prompts")
async def create_prompt_endpoint(prompt: PromptRequest):
    prompt_id = create_prompt(prompt.name, prompt.content, prompt.description)
    return {"id": prompt_id, "message": "Prompt created"}

@router.put("/prompts/{prompt_id}")
async def update_prompt_endpoint(prompt_id: int, prompt: PromptRequest):
    update_prompt(prompt_id, prompt.name, prompt.content, prompt.description)
    return {"message": "Prompt updated"}

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    prompt_id: Optional[int] = Form(None)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    job_id = str(uuid.uuid4())
    file_location = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    
    # Resolve prompt text
    used_prompt_text = None
    if prompt_id:
        p = get_prompt(prompt_id)
        if p:
            used_prompt_text = p['content']

    # Create job in DB, passing original filename and used prompt
    create_job(job_id, original_filename=file.filename, used_prompt=used_prompt_text)
    
    # Start background task with optional custom prompt
    background_tasks.add_task(process_pdf_background, job_id, file_location, used_prompt_text)
    
    return {"job_id": job_id, "status": "queued"}

@router.get("/jobs")
async def list_jobs():
    """List all jobs history"""
    return get_all_jobs()

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Legacy polling endpoint (optional, kept for compatibility)"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/jobs/{job_id}/cancel")
async def cancel_job_endpoint(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Only cancel if actively processing/queued
    if job['status'] in ['processing', 'queued']:
        cancel_job(job_id)
        return {"message": "Job cancellation requested"}
    
    return {"message": "Job is already completed or cancelled"}

@router.delete("/jobs/{job_id}")
async def delete_job_endpoint(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    delete_job(job_id)
    # Also try to clean up files if they exist
    # (Optional enhancement: structured file cleanup)
    return {"message": "Job deleted successfully"}

@router.get("/status/{job_id}/stream")
async def stream_status(job_id: str):
    """Server-Sent Events (SSE) endpoint for real-time updates"""
    async def event_generator():
        while True:
            job = get_job(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break
                
            data = json.dumps(dict(job))
            yield f"data: {data}\n\n"
            
            if job["status"] in ["completed", "error"]:
                break
                
            await asyncio.sleep(0.5) # Poll DB every 500ms without blocking server

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/result/{job_id}")
async def get_result(job_id: str):
    from backend.database import get_job_pages
    
    pages = get_job_pages(job_id)
    # Return as list of dicts: [{ "page_number": 1, "content": "..." }, ...]
    # Remap keys if necessary to match frontend Expectations (currently page.page, page.text)
    # The DB returns row['page_number'] so we map it.
    
    return [
        {"page": row["page_number"], "text": row["content"]}
        for row in pages
    ]

@router.get("/download/{job_id}/{format}")
async def download_file(job_id: str, format: str):
    if format not in ["xlsx", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid format")
    
    # Generate file on-demand from DB (RAM efficient)
    from backend.database import get_job_pages
    import pandas as pd
    
    pages = get_job_pages(job_id)
    if not pages:
        raise HTTPException(status_code=404, detail="No data found for this job")
        
    df = pd.DataFrame(pages)
    
    # Use output filename
    filename = f"export_{job_id}.{format}"
    file_path = os.path.join(PROCESSED_DIR, filename)
    
    # Generate file only if requested (or overwrite existing to be safe)
    if format == "xlsx":
        df.to_excel(file_path, index=False)
    else:
        df.to_csv(file_path, index=False)
        
    return FileResponse(file_path, filename=filename)

@router.get("/export/{job_id}")
async def export_data(job_id: str, format: str = "excel"):
    # Redirect to the new download handler logic
    file_format = "xlsx" if format == "excel" else "csv"
    return await download_file(job_id, file_format)
