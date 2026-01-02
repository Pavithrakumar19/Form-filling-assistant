"""
Smart PDF Extractor - Improved Version
======================================
Better name extraction and data handling
"""

import PyPDF2
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import re
from typing import Dict, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')

# Uncomment and set your Tesseract path on Windows
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class SmartPDFExtractor:
    """Enhanced PDF extraction with better name detection"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.text = ""
        self.data: Dict[str, str] = {}
        self.qa_pipeline = None
    
    def _init_bert(self):
        """Lazy initialization of BERT Q&A model"""
        if self.qa_pipeline is None:
            try:
                from transformers import pipeline
                print("Loading BERT model...")
                self.qa_pipeline = pipeline(
                    "question-answering",
                    model="deepset/bert-base-cased-squad2",
                    tokenizer="deepset/bert-base-cased-squad2"
                )
                print("✓ BERT model loaded")
            except Exception as e:
                print(f"Warning: BERT not available - {e}")
                self.qa_pipeline = None
    
    def extract_text(self) -> str:
        """Extract text using multiple methods"""
        texts = []
        
        # Method 1: PyPDF2
        try:
            print("Trying PyPDF2 extraction...")
            with open(self.pdf_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and len(text.strip()) > 50:
                        texts.append(text)
            if texts:
                print(f"✓ PyPDF2 extracted {sum(len(t) for t in texts)} characters")
        except Exception as e:
            print(f"PyPDF2 failed: {e}")
        
        # Method 2: PDFPlumber
        try:
            print("Trying PDFPlumber extraction...")
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and len(text.strip()) > 50:
                        texts.append(text)
            if texts:
                print(f"✓ PDFPlumber extracted {sum(len(t) for t in texts)} characters")
        except Exception as e:
            print(f"PDFPlumber failed: {e}")
        
        # Method 3: OCR if needed
        if not texts or sum(len(t) for t in texts) < 200:
            try:
                print("Trying OCR extraction...")
                images = convert_from_path(self.pdf_path, dpi=300, first_page=1, last_page=3)
                for img in images:
                    text = pytesseract.image_to_string(img, lang='eng')
                    if text and len(text.strip()) > 50:
                        texts.append(text)
                if texts:
                    print(f"✓ OCR extracted {sum(len(t) for t in texts)} characters")
            except Exception as e:
                print(f"OCR failed: {e}")
        
        self.text = "\n\n".join(texts)
        print(f"✓ Total extracted: {len(self.text)} characters")
        
        return self.text
    
    def extract_structured_data(self) -> Dict[str, str]:
        """Extract structured data using regex patterns"""
        text = self.text
        
        patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+91[\s-]?)?[6-9]\d{9}\b',
            'aadhaar': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'pan': r'\b[A-Z]{5}\d{4}[A-Z]\b',
            'pincode': r'\b\d{6}\b',
            'date': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        }
        
        print("\nExtracting structured data...")
        
        for key, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                self.data[key] = matches[0].strip()
                print(f"✓ Found {key}: {self.data[key]}")
        
        # Extract NAME with improved logic
        name = self.extract_name_improved()
        if name:
            self.data['name'] = name
            print(f"✓ Found name: {name}")
        
        # Extract ADDRESS
        address = self.extract_address()
        if address:
            self.data['address'] = address
            print(f"✓ Found address: {address}")
        
        return self.data
    
    def extract_name_improved(self) -> Optional[str]:
        """Improved name extraction with multiple strategies"""
        
        # Strategy 1: Look for name patterns in Aadhaar cards
        lines = self.text.split('\n')
        
        skip_words = {
            'government', 'india', 'aadhaar', 'unique', 'authority',
            'male', 'female', 'dob', 'birth', 'year', 'card', 'number',
            'address', 'pin', 'code', 'state', 'district', 'post',
            'income', 'tax', 'department', 'permanent', 'account',
            'republic', 'signature', 'photo', 'date', 'issue', 'issued',
            'enrollment', 'help', 'resident', 'identity', 'www', 'uidai'
        }
        
        potential_names = []
        
        for line in lines:
            line = line.strip()
            
            if len(line) < 3 or len(line) > 100:
                continue
            
            # Skip lines with skip words
            if any(skip in line.lower() for skip in skip_words):
                continue
            
            # Skip lines with numbers
            if re.search(r'\d{2,}', line):
                continue
            
            # Skip lines with special characters (except spaces and dots)
            if re.search(r'[^A-Za-z\s\.]', line):
                continue
            
            words = line.split()
            
            # Look for 2-4 word names
            if 2 <= len(words) <= 4:
                # All words should be alphabetic
                if all(w.replace('.', '').isalpha() for w in words):
                    # First letter should be capital
                    if words[0][0].isupper():
                        # Filter out very short names
                        if len(line.replace(' ', '')) >= 4:
                            potential_names.append(line)
        
        # Return the longest name (usually most complete)
        if potential_names:
            best_name = max(potential_names, key=lambda x: len(x.replace(' ', '')))
            
            # If name is too short (like "S S"), try to find a better one
            if len(best_name.replace(' ', '')) < 6:
                # Look for names with more characters
                better_names = [n for n in potential_names if len(n.replace(' ', '')) >= 6]
                if better_names:
                    best_name = max(better_names, key=lambda x: len(x.replace(' ', '')))
            
            return best_name
        
        # Strategy 2: Use BERT if available
        self._init_bert()
        if self.qa_pipeline and len(self.text) > 50:
            try:
                result = self.qa_pipeline(
                    question="What is the person's full name?",
                    context=self.text[:2000]
                )
                if result['score'] > 0.3:
                    return result['answer'].strip()
            except Exception as e:
                print(f"BERT name extraction failed: {e}")
        
        return None
    
    def extract_address(self) -> Optional[str]:
        """Extract address from document"""
        
        # Try to find address patterns
        lines = self.text.split('\n')
        
        # Look for lines that look like addresses
        address_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Address indicators
            if any(word in line.lower() for word in ['s/o', 'c/o', 'd/o', 'w/o', 'street', 'road', 'village']):
                # Get this line and next 2-3 lines
                address_parts = [line]
                for j in range(i+1, min(i+4, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and len(next_line) > 3:
                        address_parts.append(next_line)
                
                address = ' '.join(address_parts)
                if len(address) > 20:
                    return address[:200]  # Limit length
        
        # Use BERT as fallback
        self._init_bert()
        if self.qa_pipeline and len(self.text) > 50:
            try:
                result = self.qa_pipeline(
                    question="What is the complete address?",
                    context=self.text[:2000]
                )
                if result['score'] > 0.2:
                    return result['answer'].strip()
            except Exception as e:
                print(f"BERT address extraction failed: {e}")
        
        return None
    
    def process(self) -> Tuple[str, Dict[str, str]]:
        """Complete extraction pipeline"""
        print("\n" + "="*60)
        print("EXTRACTING DATA FROM PDF")
        print("="*60)
        
        self.extract_text()
        self.extract_structured_data()
        
        print("\n" + "="*60)
        print(f"EXTRACTION COMPLETE - Found {len(self.data)} fields")
        print("="*60 + "\n")
        
        return self.text, self.data