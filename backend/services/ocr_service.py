import os
import json
import logging
from pdf2image import convert_from_path
# Placeholder for DeepSeek Model Import
# from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)

import os
import json
import logging
import torch
import pdf2image
from pdf2image import convert_from_path
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import AutoModel, AutoTokenizer
import pandas as pd

PROCESSED_DIR = "data/processed"

# Global model cache
model = None
tokenizer = None

def load_model():
    global model, tokenizer
    if model is None:
        # Default to local path if not set
        DEFAULT_PATH = "data/models/DeepSeek-OCR"
        MODEL_PATH = os.getenv("OCR_MODEL_PATH", DEFAULT_PATH)
        
        if not os.path.exists(MODEL_PATH) and MODEL_PATH == DEFAULT_PATH:
            MODEL_PATH = "deepseek-ai/DeepSeek-OCR"

        logger.info(f"Loading model from {MODEL_PATH}...")
        
        try:
            # 1. Load Tokenizer
            logger.info("Step 1: Loading Tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
            logger.info("Step 1: Tokenizer Loaded.")

            # 2. Load Model
            logger.info("Step 2: Loading Model...")
            model = AutoModel.from_pretrained(
                MODEL_PATH,
                trust_remote_code=True,
                use_safetensors=True,
                torch_dtype=torch.bfloat16,
                device_map="auto" 
            )
            # Note: Explicit .cuda().to(bfloat16) is handled by device_map="auto" + torch_dtype
            logger.info("Step 2: Model Loaded.")
            
            model = model.eval() 
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise e

from backend.database import update_job, save_result, save_page_result, get_job

def process_pdf_background(job_id: str, file_path: str):
    """
    Background task to process the PDF.
    Now SYNCHRONOUS (def instead of async def) to run in a thread pool.
    """
    logger.info(f"Starting processing for job {job_id}")
    
    try:
        # Update status: Loading Model
        update_job(job_id, status="processing", progress=0, message="Loading AI Model...")

        # Load model if not loaded
        if model is None:
             load_model()

        # Update status: Counting pages
        update_job(job_id, status="processing", progress=5, message="Analyzing PDF...")

        # 1. Get Page Count
        try:
            info = pdf2image.pdfinfo_from_path(file_path)
            total_pages = info["Pages"]
        except Exception as e:
             logger.warning(f"Could not get page count via pdfinfo: {e}, falling back to full read")
             total_pages = 1 
        
        # Check for cancellation before loop
        job_info = get_job(job_id)
        if not job_info or job_info.get('cancelled') == 1 or job_info.get('status') == 'cancelled':
            logger.info(f"Job {job_id} stopped (Cancelled or Deleted).")
            if job_info:
                update_job(job_id, status="cancelled", message="Cancelled by user")
            # Cleanup source file if needed
            return

        update_job(job_id, status="processing", progress=5, current_page=0, total_pages=total_pages)
        
        # 2. Iterate and OCR
        for i in range(1, total_pages + 1):
            # Check for cancellation or deletion inside loop
            job_info = get_job(job_id)
            logger.info(f"Checking cancellation for {job_id}: found={bool(job_info)}")
            
            # Stop if job is deleted (None) or cancelled
            if not job_info or job_info.get('cancelled') == 1 or job_info.get('status') == 'cancelled':
                logger.info(f"Job {job_id} stopped (Cancelled or Deleted).")
                if job_info: # Only update if it still exists
                    update_job(job_id, status="cancelled", message="Cancelled by user")
                return

            temp_image_path = None
            text = ""
            try:
                # Convert ONLY the current page
                images = convert_from_path(file_path, first_page=i, last_page=i, dpi=300)
                if not images:
                    break
                image = images[0].convert("RGB") # Ensure RGB
                
                # Save temp image for model.infer (requires file path)
                temp_image_path = os.path.join(PROCESSED_DIR, f"{job_id}_temp_page_{i}.png")
                image.save(temp_image_path)

                # Prepare prompt (Official Format)
                prompt = "<image>\n<|grounding|>Convert the document to markdown."
                
                # Create unique output directory for this page to avoid collisions
                page_output_dir = os.path.join(PROCESSED_DIR, f"{job_id}_page_{i}_out")
                os.makedirs(page_output_dir, exist_ok=True)

                # Inference using native .infer() method from DeepSeek-OCR
                # Note: The README suggests model.infer(...)
                text_result = model.infer(
                    tokenizer,
                    prompt=prompt,
                    image_file=temp_image_path,
                    output_path=page_output_dir,  # Save to unique dir
                    base_size=1024,
                    image_size=640,
                    crop_mode=True,
                    save_results=True, 
                    test_compress=False
                )
                
                # If model.infer returns None (it might just save a file), we need to read that file.
                if text_result is None:
                     # DeepSeek-OCR saves as 'result.mmd' (Markdown) or 'result_with_boxes.jpg'
                     expected_mmd = os.path.join(page_output_dir, "to_markdown", "result.mmd")
                     # Sometimes it's directly in the root, sometimes in subfolder. 
                     # Let's check root first based on previous ls finding "result.mmd" in PROCESSED_DIR output.
                     # If previous output was in PROCESSED_DIR, then it was likely at root.
                     
                     root_mmd = os.path.join(page_output_dir, "result.mmd")
                     
                     # Also check for "to_markdown" subfolder which some versions use
                     sub_mmd = os.path.join(page_output_dir, "to_markdown", "result.mmd")

                     if os.path.exists(root_mmd):
                         with open(root_mmd, 'r') as f:
                             text = f.read()
                     elif os.path.exists(sub_mmd):
                         with open(sub_mmd, 'r') as f:
                             text = f.read()
                     else:
                         # Last resort: Try simple file matching
                         files = os.listdir(page_output_dir)
                         md_files = [f for f in files if f.endswith('.md') or f.endswith('.mmd')]
                         if md_files:
                             with open(os.path.join(page_output_dir, md_files[0]), 'r') as f:
                                 text = f.read()
                         else:
                             text = "[Error: Could not find result.mmd in output]"
                else:
                    text = text_result

                # DEBUG LOGGING
                logger.info(f"--- Raw Model Output Page {i} ---\n{text}\n-------------------------------")
                
            except Exception as e:
                logger.error(f"Error on page {i}: {e}")
                text = f"[Error processing page {i}: {str(e)}]"
            
            # Cleanup temp file and dir
            if temp_image_path and os.path.exists(temp_image_path):
                try:
                    os.remove(temp_image_path)
                except: pass
                
            if 'page_output_dir' in locals() and os.path.exists(page_output_dir):
                import shutil
                shutil.rmtree(page_output_dir, ignore_errors=True)

            # SAVE PAGE RESULT DIRECTLY TO DB (No RAM accumulation)
            save_page_result(job_id, i, text)
            
            # Update status
            progress = int((i / total_pages) * 100)
            update_job(job_id, status="processing", progress=progress, current_page=i)

        # 3. Mark Job as Completed (Pass empty list as data is in streaming table)
        save_result(job_id, [])
            
        # Update status: Completed
        update_job(job_id, status="completed", progress=100, total_pages=total_pages)

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        # Atomic error write
        update_job(job_id, status="error", error=str(e), message="Processing Failed")

def run_deepseek_ocr(image):
    # This function is now folded into the main loop or can be separated if needed for cleaner code
    pass
