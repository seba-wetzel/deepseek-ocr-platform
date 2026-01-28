
import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import json
import asyncio
import sys

# Mock modules before importing ocr_service to avoid import errors or heavy loads
sys.modules['pdf2image'] = MagicMock()
sys.modules['deepseek_vl'] = MagicMock()
sys.modules['deepseek_vl.models'] = MagicMock()
sys.modules['deepseek_vl.utils.io'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['pandas'] = MagicMock()

# Now import the service
# We need to set the environment variable for PROCESSED_DIR to a temp dir maybe, 
# or just mock os.path and open
from backend.services import ocr_service

class TestOCRFix(unittest.IsolatedAsyncioTestCase):
    
    @patch('backend.services.ocr_service.convert_from_path')
    @patch('backend.services.ocr_service.pdf2image.pdfinfo_from_path')
    @patch('backend.services.ocr_service.load_model')
    @patch('backend.services.ocr_service.atomic_write_status')
    @patch('builtins.open', new_callable=mock_open)
    @patch('backend.services.ocr_service.json.dump')
    async def test_streaming_logic(self, mock_json_dump, mock_file, mock_atomic_status, mock_load_model, mock_pdfinfo, mock_convert):
        
        # Setup Mocks
        job_id = "test_job"
        file_path = "test.pdf"
        
        # Mock Page Count = 3
        mock_pdfinfo.return_value = {"Pages": 3}
        
        # Mock convert_from_path to return a key-able list based on calls
        # process_pdf_background calls it with first_page=i, last_page=i
        # We need it to return a list containing one "image"
        mock_convert.return_value = ["mock_image_obj"]
        
        # Run the function
        # We need to mock model execution inside the loop
        ocr_service.model = MagicMock()
        ocr_service.tokenizer = MagicMock()
        ocr_service.vl_chat_processor = MagicMock()
        
        # Mock generate return
        ocr_service.model.language_model.generate.return_value = [MagicMock()]
        ocr_service.tokenizer.decode.return_value = "Extracted Text"
        
        await ocr_service.process_pdf_background(job_id, file_path)
        
        # ASSERTIONS
        
        # 1. Verify Memory Optimization: convert_from_path called 3 times (once per page)
        # instead of 1 time for all pages.
        self.assertEqual(mock_convert.call_count, 3)
        
        # Verify arguments for each call to ensure streaming
        calls = mock_convert.call_args_list
        self.assertEqual(calls[0][1]['first_page'], 1)
        self.assertEqual(calls[0][1]['last_page'], 1)
        self.assertEqual(calls[1][1]['first_page'], 2)
        self.assertEqual(calls[1][1]['last_page'], 2)
        
        # 2. Verify Atomic Status Updates
        # Should be called multiple times: Init, Page Count, 3 pages progress, Completed
        # Init + Count + 3 * Progress + Completed = 6 calls minimum
        self.assertGreaterEqual(mock_atomic_status.call_count, 6)
        
        # Check Final Status
        mock_atomic_status.assert_called_with(job_id, {"status": "completed", "progress": 100, "total_pages": 3})

        print("\n✅ Verification Passed:")
        print("  - Streaming PDF conversion verified (Page-by-Page)")
        print("  - Atomic status updates verified")
        print("  - Loop logic correct")

if __name__ == '__main__':
    unittest.main()
