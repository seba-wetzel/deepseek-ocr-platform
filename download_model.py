import os
from huggingface_hub import snapshot_download

MODEL_NAME = "deepseek-ai/deepseek-vl-1.3b-chat"
LOCAL_DIR = "data/models/deepseek-vl-1.3b-chat"

print(f"Downloading {MODEL_NAME} to {LOCAL_DIR}...")
os.makedirs(LOCAL_DIR, exist_ok=True)

try:
    snapshot_download(
        repo_id=MODEL_NAME,
        local_dir=LOCAL_DIR,
        local_dir_use_symlinks=False,
        resume_download=True
    )
    print("Download complete!")
except Exception as e:
    print(f"Error downloading model: {e}")
    exit(1)
