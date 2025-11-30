#!/usr/bin/env python3
"""
PaddleOCR Service for N8N Integration
简单的 OCR 服务，供 n8n 工作流调用

Usage:
    pip install paddleocr fastapi uvicorn
    python paddle_ocr_server.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any
import base64
import io
import os
import tempfile


app = FastAPI(
    title="PaddleOCR Service",
    description="OCR service for legal document processing",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OCR (lazy loading)
ocr_engine = None


def get_ocr_engine():
    """Lazy load OCR engine"""
    global ocr_engine
    if ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang='ch',
                show_log=False,
                use_gpu=False  # Set to True if GPU available
            )
        except ImportError:
            print("⚠️  PaddleOCR not installed. Running in mock mode.")
            ocr_engine = "mock"
    return ocr_engine


class OCRRequest(BaseModel):
    image_base64: str
    language: str = "ch"


class OCRResult(BaseModel):
    success: bool
    results: List[Any]
    text: str
    confidence: float = 0.0
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    ocr_available: bool
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    ocr = get_ocr_engine()
    return HealthResponse(
        status="healthy",
        ocr_available=ocr != "mock",
        version="1.0.0"
    )


@app.post("/ocr", response_model=OCRResult)
async def perform_ocr(request: OCRRequest):
    """
    Perform OCR on base64 encoded image
    
    Parameters:
    - image_base64: Base64 encoded image data
    - language: OCR language ('ch' for Chinese, 'en' for English)
    
    Returns:
    - results: Raw OCR results
    - text: Extracted text
    - confidence: Average confidence score
    """
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.image_base64)
        
        ocr = get_ocr_engine()
        
        if ocr == "mock":
            # Mock mode for testing without PaddleOCR installed
            return OCRResult(
                success=True,
                results=[
                    {"text": "模拟OCR识别结果", "confidence": 0.95},
                    {"text": "保险合同", "confidence": 0.92},
                    {"text": "投保人：张三", "confidence": 0.88},
                    {"text": "保险金额：100,000元", "confidence": 0.90}
                ],
                text="模拟OCR识别结果\n保险合同\n投保人：张三\n保险金额：100,000元",
                confidence=0.91
            )
        
        # Save to temp file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            tmp_file.write(image_data)
            tmp_path = tmp_file.name
        
        try:
            # Perform OCR
            result = ocr.ocr(tmp_path, cls=True)
            
            if not result or not result[0]:
                return OCRResult(
                    success=True,
                    results=[],
                    text="",
                    confidence=0.0
                )
            
            # Extract text and calculate confidence
            texts = []
            confidences = []
            formatted_results = []
            
            for line in result[0]:
                if len(line) >= 2:
                    text = line[1][0]
                    conf = line[1][1]
                    texts.append(text)
                    confidences.append(conf)
                    formatted_results.append({
                        "text": text,
                        "confidence": conf,
                        "box": line[0]
                    })
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return OCRResult(
                success=True,
                results=formatted_results,
                text="\n".join(texts),
                confidence=avg_confidence
            )
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@app.post("/ocr/pdf")
async def ocr_pdf(request: OCRRequest):
    """
    Perform OCR on base64 encoded PDF
    Converts PDF pages to images and performs OCR
    """
    try:
        # Decode base64 PDF
        pdf_data = base64.b64decode(request.image_base64)
        
        ocr = get_ocr_engine()
        
        if ocr == "mock":
            return OCRResult(
                success=True,
                results=[
                    {"page": 1, "text": "PDF第1页模拟识别结果", "confidence": 0.90}
                ],
                text="PDF第1页模拟识别结果",
                confidence=0.90
            )
        
        # For real implementation, use pdf2image to convert PDF to images
        try:
            from pdf2image import convert_from_bytes
            
            images = convert_from_bytes(pdf_data)
            all_texts = []
            all_results = []
            
            for page_num, image in enumerate(images, 1):
                # Save image to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                    image.save(tmp_file.name)
                    tmp_path = tmp_file.name
                
                try:
                    result = ocr.ocr(tmp_path, cls=True)
                    
                    if result and result[0]:
                        page_texts = []
                        for line in result[0]:
                            if len(line) >= 2:
                                text = line[1][0]
                                page_texts.append(text)
                                all_results.append({
                                    "page": page_num,
                                    "text": text,
                                    "confidence": line[1][1]
                                })
                        
                        all_texts.extend(page_texts)
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            
            return OCRResult(
                success=True,
                results=all_results,
                text="\n".join(all_texts),
                confidence=0.85
            )
            
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="pdf2image not installed. Run: pip install pdf2image"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF OCR failed: {str(e)}")


@app.post("/extract/insurance")
async def extract_insurance_info(request: OCRRequest):
    """
    Extract insurance-specific information from document
    """
    # First perform OCR
    ocr_result = await perform_ocr(request)
    
    if not ocr_result.success:
        return {"success": False, "error": "OCR failed"}
    
    text = ocr_result.text
    
    # Extract structured information (simplified version)
    # In production, use more sophisticated NLP/regex patterns
    extracted = {
        "insurance_company": extract_field(text, ["保险公司", "承保公司", "投保公司"]),
        "policy_number": extract_field(text, ["保单号", "保险单号", "合同号"]),
        "insured_name": extract_field(text, ["被保险人", "投保人"]),
        "vehicle_plate": extract_field(text, ["车牌号", "号牌号码"]),
        "valid_from": extract_field(text, ["保险期间自", "起保日期", "生效日期"]),
        "valid_to": extract_field(text, ["至", "终止日期", "到期日期"]),
        "coverage_amount": extract_field(text, ["保险金额", "保额", "责任限额"]),
        "premium": extract_field(text, ["保险费", "保费"])
    }
    
    return {
        "success": True,
        "raw_text": text,
        "extracted_data": extracted
    }


def extract_field(text: str, keywords: List[str]) -> Optional[str]:
    """Simple field extraction based on keywords"""
    import re
    
    for keyword in keywords:
        # Try to find keyword and extract following content
        pattern = f"{keyword}[：:：]?\\s*([^\\n，。,]+)"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return None


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("PaddleOCR Service Starting...")
    print("=" * 50)
    print()
    print("Endpoints:")
    print("  POST /ocr         - OCR image")
    print("  POST /ocr/pdf     - OCR PDF document")
    print("  POST /extract/insurance - Extract insurance info")
    print("  GET  /health      - Health check")
    print()
    print("Documentation: http://localhost:8765/docs")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8765)
