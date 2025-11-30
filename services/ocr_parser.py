"""
OCR Result Parser Service
=========================

Parses OCR JSON results and extracts essential fields for legal document processing.
This module provides parsing functions for various document types:
- ID cards (身份证)
- Driver's licenses (驾驶证)
- Vehicle registration (行驶证)
- Insurance policies (保险单)
- Traffic accident reports (交通事故认定书)
- General documents

You can modify the extraction patterns and field mappings as needed.
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class DocumentType(str, Enum):
    """Supported document types for OCR parsing"""
    ID_CARD = "id_card"
    DRIVER_LICENSE = "driver_license"
    VEHICLE_REGISTRATION = "vehicle_registration"
    INSURANCE_POLICY = "insurance_policy"
    ACCIDENT_REPORT = "accident_report"
    GENERAL = "general"


class ParsedField(BaseModel):
    """A single parsed field from OCR"""
    field_name: str
    value: Any
    confidence: float = 1.0
    source_text: Optional[str] = None


class OCRParseResult(BaseModel):
    """Result of parsing OCR data"""
    success: bool
    document_type: DocumentType
    extracted_fields: Dict[str, Any]
    raw_text: Optional[str] = None
    confidence: float = 0.0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# Field Extraction Patterns
# ============================================================================

# ID Card patterns (身份证)
ID_CARD_PATTERNS = {
    "name": [
        r"姓名[：:]\s*([^\s\n,，]+)",
        r"姓\s*名\s*([^\s\n,，]+)",
    ],
    "gender": [
        r"性别[：:]\s*(男|女)",
        r"性\s*别\s*(男|女)",
    ],
    "ethnicity": [
        r"民族[：:]\s*([^\s\n,，]+)",
        r"民\s*族\s*([^\s\n,，]+)",
    ],
    "birth_date": [
        r"出生[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
        r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*出生",
    ],
    "address": [
        r"住址[：:]\s*(.+?)(?=公民身份|$)",
        r"住\s*址\s*(.+?)(?=公民|$)",
    ],
    "id_number": [
        r"公民身份号码[：:]\s*(\d{17}[\dXx])",
        r"身份证号[：:]\s*(\d{17}[\dXx])",
        r"(\d{6}\d{4}\d{2}\d{2}\d{3}[\dXx])",
    ],
}

# Driver's License patterns (驾驶证)
DRIVER_LICENSE_PATTERNS = {
    "name": [
        r"姓名[：:]\s*([^\s\n,，]+)",
    ],
    "gender": [
        r"性别[：:]\s*(男|女)",
    ],
    "license_number": [
        r"证号[：:]\s*(\d{17}[\dXx]|\d{12})",
        r"驾驶证号[：:]\s*(\d+)",
    ],
    "vehicle_type": [
        r"准驾车型[：:]\s*([A-Z]\d?)",
        r"车型[：:]\s*([A-Z]\d?)",
    ],
    "valid_from": [
        r"初次领证[：:]\s*(\d{4}-\d{2}-\d{2}|\d{4}年\d{1,2}月\d{1,2}日)",
    ],
    "valid_until": [
        r"有效期限[：:]\s*(\d{4}-\d{2}-\d{2}|\d{4}年\d{1,2}月\d{1,2}日)",
        r"至[：:]\s*(\d{4}-\d{2}-\d{2}|\d{4}年\d{1,2}月\d{1,2}日)",
    ],
}

# Insurance Policy patterns (保险单)
INSURANCE_PATTERNS = {
    "insurance_company": [
        r"([\u4e00-\u9fa5]+保险[\u4e00-\u9fa5]*公司)",
        r"承保公司[：:]\s*([^\n]+)",
    ],
    "policy_number": [
        r"保单号[：:]\s*([A-Za-z0-9\-]+)",
        r"保险单号[：:]\s*([A-Za-z0-9\-]+)",
    ],
    "insured_name": [
        r"被保险人[：:]\s*([^\s\n,，]+)",
        r"投保人[：:]\s*([^\s\n,，]+)",
    ],
    "vehicle_plate": [
        r"车牌号[：:]\s*([^\s\n,，]+)",
        r"号牌号码[：:]\s*([^\s\n,，]+)",
        r"([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{5,6})",
    ],
    "coverage_amount": [
        r"保险金额[：:]\s*([\d,\.]+)\s*元?",
        r"保额[：:]\s*([\d,\.]+)\s*元?",
        r"责任限额[：:]\s*([\d,\.]+)\s*元?",
    ],
    "premium": [
        r"保险费[：:]\s*([\d,\.]+)\s*元?",
        r"保费[：:]\s*([\d,\.]+)\s*元?",
    ],
    "valid_from": [
        r"保险期间[：:]\s*自\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"起保日期[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
    ],
    "valid_until": [
        r"至\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"终止日期[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
    ],
}

# Traffic Accident Report patterns (交通事故认定书)
ACCIDENT_REPORT_PATTERNS = {
    "case_number": [
        r"编号[：:]\s*([^\s\n]+)",
        r"案号[：:]\s*([^\s\n]+)",
    ],
    "accident_date": [
        r"(\d{4})年(\d{1,2})月(\d{1,2})日(\d{1,2})时(\d{1,2})分",
        r"事故发生时间[：:]\s*(.+?)(?=\s|$)",
    ],
    "accident_location": [
        r"事故地点[：:]\s*(.+?)(?=当事人|$)",
        r"发生地点[：:]\s*(.+?)(?=\n|$)",
    ],
    "party_a_name": [
        r"甲方[：:]\s*([^\s\n,，]+)",
        r"当事人甲[：:]\s*([^\s\n,，]+)",
    ],
    "party_b_name": [
        r"乙方[：:]\s*([^\s\n,，]+)",
        r"当事人乙[：:]\s*([^\s\n,，]+)",
    ],
    "responsibility": [
        r"(全部责任|主要责任|同等责任|次要责任|无责任)",
    ],
}


# ============================================================================
# Parsing Functions
# ============================================================================

def extract_field(text: str, patterns: List[str]) -> Optional[str]:
    """
    Extract a field value using multiple regex patterns.
    Returns the first match found.
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            # Return the first capturing group if it exists, otherwise the whole match
            if match.groups():
                # Handle multi-group patterns (like dates)
                if len(match.groups()) > 1:
                    return "-".join(match.groups())
                return match.group(1).strip()
            return match.group(0).strip()
    return None


def detect_document_type(text: str) -> DocumentType:
    """
    Detect the type of document based on keywords in the text.
    """
    text_lower = text.lower()
    
    # Check for ID card
    if any(kw in text for kw in ["身份证", "公民身份号码", "居民身份证"]):
        return DocumentType.ID_CARD
    
    # Check for driver's license
    if any(kw in text for kw in ["驾驶证", "准驾车型", "机动车驾驶证"]):
        return DocumentType.DRIVER_LICENSE
    
    # Check for vehicle registration
    if any(kw in text for kw in ["行驶证", "机动车行驶证", "车辆识别代号"]):
        return DocumentType.VEHICLE_REGISTRATION
    
    # Check for insurance policy
    if any(kw in text for kw in ["保险单", "保险公司", "保险期间", "保险金额", "投保人"]):
        return DocumentType.INSURANCE_POLICY
    
    # Check for accident report
    if any(kw in text for kw in ["事故认定书", "交通事故", "责任认定"]):
        return DocumentType.ACCIDENT_REPORT
    
    return DocumentType.GENERAL


def parse_id_card(text: str) -> Dict[str, Any]:
    """Parse ID card OCR result"""
    result = {}
    
    for field_name, patterns in ID_CARD_PATTERNS.items():
        value = extract_field(text, patterns)
        if value:
            # Clean up address
            if field_name == "address":
                value = value.replace("\n", "").strip()
            result[field_name] = value
    
    # Map to filler format
    mapped = {
        "id_card_name": result.get("name"),
        "id_card_gender": result.get("gender"),
        "id_card_race": result.get("ethnicity"),
        "id_card_dob": result.get("birth_date"),
        "id_card_address": result.get("address"),
        "id_card_number": result.get("id_number"),
    }
    
    # Remove None values
    return {k: v for k, v in mapped.items() if v is not None}


def parse_driver_license(text: str) -> Dict[str, Any]:
    """Parse driver's license OCR result"""
    result = {}
    
    for field_name, patterns in DRIVER_LICENSE_PATTERNS.items():
        value = extract_field(text, patterns)
        if value:
            result[field_name] = value
    
    # Map to filler format
    mapped = {
        "driver_name": result.get("name"),
        "driver_gender": result.get("gender"),
        "driver_license_number": result.get("license_number"),
        "driver_vehicle_type": result.get("vehicle_type"),
        "driver_license_valid_from": result.get("valid_from"),
        "driver_license_valid_until": result.get("valid_until"),
    }
    
    return {k: v for k, v in mapped.items() if v is not None}


def parse_insurance_policy(text: str) -> Dict[str, Any]:
    """Parse insurance policy OCR result"""
    result = {}
    
    for field_name, patterns in INSURANCE_PATTERNS.items():
        value = extract_field(text, patterns)
        if value:
            result[field_name] = value
    
    # Map to filler format
    mapped = {
        "insurance_company": result.get("insurance_company"),
        "insurance_policy_number": result.get("policy_number"),
        "insurance_insured_name": result.get("insured_name"),
        "insurance_vehicle_plate": result.get("vehicle_plate"),
        "insurance_coverage": result.get("coverage_amount"),
        "insurance_premium": result.get("premium"),
        "insurance_valid_from": result.get("valid_from"),
        "insurance_valid_until": result.get("valid_until"),
    }
    
    return {k: v for k, v in mapped.items() if v is not None}


def parse_accident_report(text: str) -> Dict[str, Any]:
    """Parse traffic accident report OCR result"""
    result = {}
    
    for field_name, patterns in ACCIDENT_REPORT_PATTERNS.items():
        value = extract_field(text, patterns)
        if value:
            result[field_name] = value
    
    # Map to filler format
    mapped = {
        "accident_case_number": result.get("case_number"),
        "accident_date": result.get("accident_date"),
        "accident_location": result.get("accident_location"),
        "accident_party_a": result.get("party_a_name"),
        "accident_party_b": result.get("party_b_name"),
        "accident_responsibility": result.get("responsibility"),
    }
    
    return {k: v for k, v in mapped.items() if v is not None}


def parse_general_document(text: str) -> Dict[str, Any]:
    """
    Parse general document - extract common fields.
    Can be extended for specific document types.
    """
    result = {}
    
    # Try to extract common fields
    # Names
    name_patterns = [r"姓名[：:]\s*([^\s\n,，]+)", r"当事人[：:]\s*([^\s\n,，]+)"]
    name = extract_field(text, name_patterns)
    if name:
        result["extracted_name"] = name
    
    # Phone numbers
    phone_patterns = [r"电话[：:]\s*(\d{11})", r"联系方式[：:]\s*(\d{11})", r"(\d{3}[-\s]?\d{4}[-\s]?\d{4})"]
    phone = extract_field(text, phone_patterns)
    if phone:
        result["extracted_phone"] = phone.replace("-", "").replace(" ", "")
    
    # Amounts
    amount_patterns = [r"金额[：:]\s*([\d,\.]+)\s*元?", r"([\d,]+)\s*元"]
    amount = extract_field(text, amount_patterns)
    if amount:
        result["extracted_amount"] = amount.replace(",", "")
    
    # Dates
    date_patterns = [r"(\d{4}年\d{1,2}月\d{1,2}日)", r"(\d{4}-\d{2}-\d{2})", r"(\d{4}/\d{2}/\d{2})"]
    date = extract_field(text, date_patterns)
    if date:
        result["extracted_date"] = date
    
    return result


# ============================================================================
# Main Parser Class
# ============================================================================

class OCRResultParser:
    """
    Main parser class for OCR results.
    
    Usage:
        parser = OCRResultParser()
        result = parser.parse(ocr_json)
        
        # Or parse with known document type
        result = parser.parse(ocr_json, document_type=DocumentType.ID_CARD)
    """
    
    def __init__(self):
        self.parsers = {
            DocumentType.ID_CARD: parse_id_card,
            DocumentType.DRIVER_LICENSE: parse_driver_license,
            DocumentType.INSURANCE_POLICY: parse_insurance_policy,
            DocumentType.ACCIDENT_REPORT: parse_accident_report,
            DocumentType.VEHICLE_REGISTRATION: parse_general_document,  # TODO: Add specific parser
            DocumentType.GENERAL: parse_general_document,
        }
    
    def parse(
        self, 
        ocr_result: Dict[str, Any], 
        document_type: Optional[DocumentType] = None
    ) -> OCRParseResult:
        """
        Parse OCR result and extract essential fields.
        
        Args:
            ocr_result: OCR JSON result (from PaddleOCR service)
            document_type: Optional document type override
            
        Returns:
            OCRParseResult with extracted fields
        """
        errors = []
        warnings = []
        
        # Extract text from OCR result
        raw_text = self._extract_text(ocr_result)
        if not raw_text:
            return OCRParseResult(
                success=False,
                document_type=DocumentType.GENERAL,
                extracted_fields={},
                errors=["No text found in OCR result"]
            )
        
        # Detect document type if not provided
        if document_type is None:
            document_type = detect_document_type(raw_text)
        
        # Get the appropriate parser
        parser_func = self.parsers.get(document_type, parse_general_document)
        
        # Parse the text
        try:
            extracted_fields = parser_func(raw_text)
        except Exception as e:
            errors.append(f"Parsing error: {str(e)}")
            extracted_fields = {}
        
        # Calculate confidence based on how many fields were extracted
        if document_type == DocumentType.ID_CARD:
            expected_fields = 6
        elif document_type == DocumentType.INSURANCE_POLICY:
            expected_fields = 8
        else:
            expected_fields = 4
        
        confidence = min(1.0, len(extracted_fields) / expected_fields)
        
        # Add warnings for missing important fields
        if document_type == DocumentType.ID_CARD:
            if "id_card_name" not in extracted_fields:
                warnings.append("Could not extract name from ID card")
            if "id_card_number" not in extracted_fields:
                warnings.append("Could not extract ID number from ID card")
        
        return OCRParseResult(
            success=len(extracted_fields) > 0,
            document_type=document_type,
            extracted_fields=extracted_fields,
            raw_text=raw_text,
            confidence=confidence,
            errors=errors,
            warnings=warnings
        )
    
    def _extract_text(self, ocr_result: Dict[str, Any]) -> str:
        """Extract plain text from OCR result structure"""
        # Handle different OCR result formats
        
        # Format 1: {text: "...", results: [...]}
        if isinstance(ocr_result, dict):
            if "text" in ocr_result:
                return ocr_result["text"]
            
            if "results" in ocr_result:
                texts = []
                for item in ocr_result["results"]:
                    if isinstance(item, dict) and "text" in item:
                        texts.append(item["text"])
                    elif isinstance(item, str):
                        texts.append(item)
                return "\n".join(texts)
            
            # Format 2: {raw_text: "..."}
            if "raw_text" in ocr_result:
                return ocr_result["raw_text"]
            
            # Format 3: {extracted_data: {...}}
            if "extracted_data" in ocr_result:
                # Already parsed, convert back to text for re-parsing
                data = ocr_result["extracted_data"]
                return "\n".join(f"{k}: {v}" for k, v in data.items() if v)
        
        # Format 4: List of text lines
        if isinstance(ocr_result, list):
            texts = []
            for item in ocr_result:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                elif isinstance(item, str):
                    texts.append(item)
            return "\n".join(texts)
        
        # Format 5: Plain string
        if isinstance(ocr_result, str):
            return ocr_result
        
        return ""
    
    def parse_to_filler_format(
        self, 
        ocr_result: Dict[str, Any],
        document_type: Optional[DocumentType] = None
    ) -> Dict[str, Any]:
        """
        Parse OCR result and return data in document filler format.
        
        This is a convenience method that returns just the extracted fields
        ready to be used with the DocumentFillerService.
        """
        result = self.parse(ocr_result, document_type)
        return result.extracted_fields if result.success else {}


# ============================================================================
# Convenience Functions
# ============================================================================

def parse_ocr_result(
    ocr_result: Dict[str, Any],
    document_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to parse OCR result.
    
    Args:
        ocr_result: OCR JSON result
        document_type: Optional type string (id_card, insurance_policy, etc.)
        
    Returns:
        Dictionary of extracted fields
    """
    parser = OCRResultParser()
    
    doc_type = None
    if document_type:
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            pass
    
    return parser.parse_to_filler_format(ocr_result, doc_type)


def parse_and_map_to_questionnaire(
    ocr_result: Dict[str, Any],
    document_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parse OCR result and map to questionnaire field format.
    
    Returns fields that can be used to pre-fill questionnaire answers.
    """
    parsed = parse_ocr_result(ocr_result, document_type)
    
    # Map from OCR fields to questionnaire question IDs
    QUESTIONNAIRE_MAPPING = {
        # ID Card to questionnaire
        "id_card_name": "q1",
        "id_card_gender": "q3",
        "id_card_dob": "q4",
        "id_card_race": "q5",
        "id_card_address": "q7",
        # Insurance to questionnaire
        "insurance_company": "q16",
        "insurance_policy_number": "q17",
        # Accident to questionnaire
        "accident_date": "q10",
        "accident_location": "q11",
    }
    
    mapped = {}
    for ocr_field, q_id in QUESTIONNAIRE_MAPPING.items():
        if ocr_field in parsed:
            mapped[q_id] = {
                "value": parsed[ocr_field],
                "source": "ocr",
                "auto_filled": True
            }
    
    return mapped


# ============================================================================
# Singleton instance for convenience
# ============================================================================

_parser_instance: Optional[OCRResultParser] = None


def get_parser() -> OCRResultParser:
    """Get or create the parser instance"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = OCRResultParser()
    return _parser_instance
