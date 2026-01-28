import sys
print("Checking imports...")
try:
    import fastapi
    import uvicorn
    import python_multipart
    import torch
    import transformers
    import accelerate
    import bitsandbytes
    import pdf2image
    from backend.main import app
    print("Imports successful. Backend structure seems valid.")
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"General Error: {e}")
    sys.exit(1)
