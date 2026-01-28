import sqlite3
import json
import os
import logging
from datetime import datetime

DB_PATH = "data/ocr.db"
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database with the jobs table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create jobs table if not exists (Basic schema)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        status TEXT,
        progress INTEGER,
        result_json TEXT,  -- Legacy field
        error TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Simple migration checks for new columns
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'original_filename' not in columns:
        print("Migrating: Adding original_filename to jobs")
        cursor.execute("ALTER TABLE jobs ADD COLUMN original_filename TEXT")
        
    if 'cancelled' not in columns:
        print("Migrating: Adding cancelled to jobs")
        cursor.execute("ALTER TABLE jobs ADD COLUMN cancelled BOOLEAN DEFAULT 0")

    # Remove total_pages and current_page if they exist (manual cleanup or more complex migration needed for data)
    # For simplicity, we're just ensuring they are not in the CREATE TABLE statement above.
    # If they exist from a previous schema, they will remain unless explicitly dropped.
    
    # Prompts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prompts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        content TEXT NOT NULL,
        description TEXT,
        is_default BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Seed default prompt if table is empty
    cursor.execute("SELECT COUNT(*) FROM prompts")
    if cursor.fetchone()[0] == 0:
        default_prompt = "<image>\n<|grounding|>Convert the document to markdown."
        cursor.execute(
            "INSERT INTO prompts (name, content, description, is_default) VALUES (?, ?, ?, ?)",
            ("Default OCR", default_prompt, "Standard DeepSeek-OCR prompt", 1)
        )

    # ... migrations ...
    if 'original_filename' not in columns:
        print("Migrating: Adding original_filename to jobs")
        cursor.execute("ALTER TABLE jobs ADD COLUMN original_filename TEXT")
        
    if 'cancelled' not in columns:
        print("Migrating: Adding cancelled to jobs")
        cursor.execute("ALTER TABLE jobs ADD COLUMN cancelled BOOLEAN DEFAULT 0")

    if 'used_prompt' not in columns:
         print("Migrating: Adding used_prompt to jobs")
         cursor.execute("ALTER TABLE jobs ADD COLUMN used_prompt TEXT")

    # ... rest of init_db ...

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            page_number INTEGER,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_pages_job_id ON job_pages(job_id)")
    
    conn.commit()
    conn.close()

def create_job(job_id, original_filename=None, used_prompt=None):
    """Create a new job with initial status."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (id, status, progress, original_filename, used_prompt) VALUES (?, ?, ?, ?, ?)",
        (job_id, 'queued', 0, original_filename, used_prompt)
    )
    conn.commit()
    conn.close()

# ... update_job, cancel_job, delete_job ...

def get_prompts():
    """Get all prompts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prompts ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_prompt(prompt_id):
    """Get a prompt by ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_prompt(name, content, description=""):
    """Create a new prompt."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO prompts (name, content, description) VALUES (?, ?, ?)",
        (name, content, description)
    )
    prompt_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return prompt_id

def update_prompt(prompt_id, name, content, description=""):
    """Update an existing prompt."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE prompts SET name = ?, content = ?, description = ? WHERE id = ?",
        (name, content, description, prompt_id)
    )
    conn.commit()
    conn.close()

# ... rest of existing functions ...
# (I will insert these new functions before 'update_job' to keep flow or append at end. 
# Better: Append Prompts CRUD at the end or logic grouping.
# Actually, I am replacing lines 44-165, so I need to be careful to include everything I cut.)
# Re-reading: I will target specific blocks to avoid massive replacement risk.

# Block 1: init_db extensions


def update_job(job_id, **kwargs):
    """
    Update job fields dynamically.
    kwargs: dictionary of fields to update (status, progress, message, etc.)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values())
    values.append(job_id)
    
    try:
        cursor.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to update job {job_id}: {e}")
    finally:
        conn.close()

def cancel_job(job_id):
    """Mark a job as cancelled."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET cancelled = 1, status = 'cancelled' WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

def delete_job(job_id):
    """Delete a job and its pages."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    cursor.execute("DELETE FROM job_pages WHERE job_id = ?", (job_id,))
    conn.commit()
    conn.close()

def get_all_jobs():
    """Get all jobs ordered by creation time (newest first)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_job(job_id):
    """Get job details as a dictionary."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def save_page_result(job_id, page_number, content):
    """Save a single page result to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO job_pages (job_id, page_number, content) VALUES (?, ?, ?)",
        (job_id, page_number, content)
    )
    conn.commit()
    conn.close()

def get_job_pages(job_id):
    """Retrieve all pages for a specific job."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT page_number, content FROM job_pages WHERE job_id = ? ORDER BY page_number ASC", (job_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_result(job_id, result_data):
    """
    Mark job as completed. 
    Legacy support: result_data might be passed, but we rely on job_pages now.
    We'll store a summary or empty list in result_json to keep schema valid.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE jobs SET result_json = ?, status = 'completed', progress = 100, message = 'Completed' WHERE id = ?",
        (json.dumps(result_data), job_id)
    )
    conn.commit()
    conn.close()
