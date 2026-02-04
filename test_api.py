"""
Test script for FastAPI OCR endpoint
"""
import sys
import time
import requests
from pathlib import Path

def test_ocr_endpoint():
    """Test the OCR endpoint with facture_1.pdf"""
    
    # File to test
    test_file = Path("/home/user/uploaded_files/facture_1.pdf")
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    # API endpoint
    url = "http://localhost:8080/ocr"
    
    print("=" * 80)
    print("Testing OCR Endpoint")
    print("=" * 80)
    print(f"File: {test_file.name}")
    print(f"Endpoint: {url}")
    print()
    
    try:
        # Open file and send POST request
        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "application/pdf")}
            data = {
                "source_entreprise": "auto-detect",
                "force_full_ocr": False
            }
            
            print("Sending request...")
            start_time = time.time()
            
            response = requests.post(url, files=files, data=data, timeout=60)
            
            elapsed = time.time() - start_time
            
            print(f"Response status: {response.status_code}")
            print(f"Elapsed time: {elapsed:.2f}s")
            print()
            
            if response.status_code == 200:
                result = response.json()
                
                print("✅ OCR Success!")
                print()
                print(f"Document ID: {result['document_id']}")
                print(f"Document Type: {result['document_type']}")
                print(f"Level: {result['level']}")
                print(f"Confidence: {result['confidence']:.2f}%")
                print(f"Source Entreprise: {result['entreprise_source']}")
                print()
                
                # Check logs for OCR mode
                logs = result.get('logs', [])
                ocr_mode_logs = [log for log in logs if 'OCR_MODE' in log or 'PDF_TEXT_DETECTED' in log]
                
                if ocr_mode_logs:
                    print("OCR Mode Logs:")
                    for log in ocr_mode_logs:
                        print(f"  {log}")
                    print()
                
                # Check extracted fields
                fields = result.get('fields', {})
                print(f"Extracted fields: {len(fields)}")
                for name, field in fields.items():
                    print(f"  - {name}: {field['value']} (confidence: {field['confidence']:.2f}%)")
                
                print()
                print("=" * 80)
                print("✅ TEST PASSED")
                print("=" * 80)
                
                return True
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(response.text)
                return False
                
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on port 8080?")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_ocr_endpoint()
    sys.exit(0 if success else 1)
