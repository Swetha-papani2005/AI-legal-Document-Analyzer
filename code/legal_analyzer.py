# legal_core.py
import re
from difflib import SequenceMatcher
from PyPDF2 import PdfReader

# Clause keywords
CLAUSES = {
    "Confidentiality": ["confidential", "non-disclosure", "nda"],
    "Termination": ["terminate", "termination", "cancel", "expiry"],
    "Liability": ["liability", "indemnify", "damages"],
    "Payment": ["payment", "fee", "price", "invoice"],
    "Jurisdiction": ["jurisdiction", "governing law", "court", "dispute"],
    "Force Majeure": ["force majeure", "unforeseeable", "act of god"],
    "Arbitration": ["arbitration", "arbitrator", "dispute resolution"],
}

# Detect contract type
CONTRACT_TYPES = {
    "Employment Contract": ["employee", "employer", "salary", "job", "position"],
    "Service Agreement": ["service", "provider", "client", "deliverables"],
    "Sales Agreement": ["product", "buyer", "seller", "price", "goods"],
    "Lease Agreement": ["tenant", "landlord", "rent", "property", "lease"],
    "Power Purchase Agreement": ["electricity", "power supply", "tariff", "energy", "plant"],
    "Legal Judgment/Case": ["versus", "petitioner", "respondent", "court", "judgment"],
}

def extract_text_from_pdf(path):
    """Extracts text from PDF using PyPDF2"""
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def summarize_text(text, n_sentences=5):
    """Creates a short summary of the legal document"""
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    return " . ".join(sentences[:n_sentences]) + ("" if len(sentences) <= n_sentences else " ...")

def detect_clauses(text):
    """Detects key legal clauses in the document"""
    found = []
    for clause, keywords in CLAUSES.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
                found.append(clause)
                break
    return found

def detect_contract_type(text):
    """Guesses the type of contract based on keywords"""
    for contract, keywords in CONTRACT_TYPES.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
                return contract
    return "General Legal Document"

def compare_versions(text1, text2):
    """Compares two versions of a document"""
    ratio = SequenceMatcher(None, text1, text2).ratio()
    return round(ratio * 100, 2)