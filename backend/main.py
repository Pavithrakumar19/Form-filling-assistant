"""
AI Form Filler - FastAPI Backend
=================================
Main application file - Windows compatible version
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Optional
import os
import shutil
from pathlib import Path
import traceback
import sys
import asyncio

# ============================================================
# CRITICAL FIX FOR WINDOWS
# ============================================================
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("✓ Windows event loop policy set")
# ============================================================

# Import our modules
from extractor import SmartPDFExtractor
from form_filler_sync import GoogleFormFiller  # Using sync version

# Initialize FastAPI
app = FastAPI(
    title="AI Form Filler API",
    description="Extract data from PDFs and auto-fill web forms",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

print("\n" + "="*60)
print("📁 Directories created:")
print(f"   Upload: {UPLOAD_DIR.absolute()}")
print(f"   Output: {OUTPUT_DIR.absolute()}")
print("="*60)


# Pydantic models
class FormFillRequest(BaseModel):
    form_url: str
    data: Dict[str, str]


class ExtractionResponse(BaseModel):
    success: bool
    extracted_data: Dict[str, str]
    text_length: int
    message: str


class FormFillResponse(BaseModel):
    success: bool
    fields_filled: int
    total_fields: int
    success_rate: str
    screenshot: Optional[str]
    message: str


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "AI Form Filler API",
        "version": "1.0.0",
        "platform": sys.platform,
        "endpoints": [
            "/extract",
            "/fill-form",
            "/download/{filename}",
            "/docs"
        ]
    }


@app.post("/extract", response_model=ExtractionResponse)
async def extract_pdf_data(file: UploadFile = File(...)):
    """Extract structured data from uploaded PDF"""
    
    print(f"\n{'='*60}")
    print(f"📥 RECEIVED FILE UPLOAD")
    print(f"{'='*60}")
    print(f"Filename: {file.filename}")
    print(f"Content-Type: {file.content_type}")
    print(f"{'='*60}\n")
    
    if not file.filename.lower().endswith('.pdf'):
        print("❌ Invalid file type")
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are supported."
        )
    
    file_path = UPLOAD_DIR / file.filename
    
    try:
        print(f"💾 Saving file to: {file_path}")
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        file_size = os.path.getsize(file_path)
        print(f"✓ File saved ({file_size} bytes)\n")
        
        print("🔍 Starting extraction...")
        extractor = SmartPDFExtractor(str(file_path))
        text, extracted_data = extractor.process()
        
        print(f"🗑️ Cleaning up...")
        os.remove(file_path)
        print(f"✓ Cleanup complete\n")
        
        response = ExtractionResponse(
            success=True,
            extracted_data=extracted_data,
            text_length=len(text),
            message=f"Successfully extracted {len(extracted_data)} fields"
        )
        
        print(f"✅ SUCCESS - Returning {len(extracted_data)} fields\n")
        return response
        
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@app.post("/fill-form", response_model=FormFillResponse)
def fill_google_form_sync(request: FormFillRequest):
    """Fill Google Form - Synchronous endpoint for Windows compatibility"""
    
    print(f"\n{'='*60}")
    print(f"📝 FILLING FORM")
    print(f"{'='*60}")
    print(f"URL: {request.form_url}")
    print(f"Data fields: {list(request.data.keys())}")
    print(f"{'='*60}\n")
    
    try:
        if not request.form_url.startswith(('http://', 'https://')):
            request.form_url = 'https://' + request.form_url
        
        # Use sync form filler
        filler = GoogleFormFiller()
        filled, total, screenshot = filler.fill_form(
            request.form_url,
            request.data
        )
        
        success_rate = f"{(filled/total*100):.1f}%" if total > 0 else "0%"
        
        response = FormFillResponse(
            success=True,
            fields_filled=filled,
            total_fields=total,
            success_rate=success_rate,
            screenshot=screenshot,
            message=f"Successfully filled {filled}/{total} fields ({success_rate})"
        )
        
        print(f"✅ SUCCESS - Filled {filled}/{total} fields\n")
        return response
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Form filling failed: {str(e)}"
        )


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated files"""
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )


@app.delete("/cleanup")
async def cleanup_files():
    """Clean up old files"""
    try:
        for file in UPLOAD_DIR.glob("*"):
            if file.is_file():
                os.remove(file)
        
        for file in OUTPUT_DIR.glob("*"):
            if file.is_file():
                os.remove(file)
        
        return {"success": True, "message": "Cleanup successful"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 Starting AI Form Filler API Server")
    print("="*60)
    print(f"\n🖥️  Platform: {sys.platform}")
    print("\n📍 Server will be available at:")
    print("   - API: http://localhost:8000")
    print("   - Docs: http://localhost:8000/docs")
    print("\n💡 Using sync Playwright for Windows compatibility")
    print("\n⚠️  Press CTRL+C to stop\n")
    print("="*60 + "\n")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )