# legal_core.py
# Backend AI logic for the AI Legal Document Analyzer
# Robust text extraction, OCR fallback, summarization, clause detection,
# improved contract-type detection (better at distinguishing court judgments
# from actual contract types), entity heuristics, risk assessment and comparison.

import re
from difflib import SequenceMatcher

# Optional dependencies - import if available, otherwise set to None
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    import docx
except Exception:
    docx = None

# -------------------------
# PDF / DOC / TXT TEXT EXTRACTION
# -------------------------
def extract_text_from_pdf(path: str) -> str:
    """
    Extract embedded text from a PDF using PyPDF2 (if available).
    Returns a concatenated string (or empty string on failure).
    """
    if not PdfReader:
        return ""

    text = []
    try:
        reader = PdfReader(path)
        for p in reader.pages:
            try:
                pg_text = p.extract_text()
            except Exception:
                pg_text = None
            if pg_text:
                text.append(pg_text)
    except Exception:
        return ""
    return "\n".join(text).strip()

def extract_text_from_docx(path: str) -> str:
    if not docx:
        return ""
    try:
        d = docx.Document(path)
        paras = [p.text for p in d.paragraphs if p.text and p.text.strip()]
        return "\n".join(paras)
    except Exception:
        return ""

def extract_text_from_txt(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        try:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception:
            return ""

# -------------------------
# OCR for scanned PDFs
# -------------------------
def run_ocr_on_pdf(path: str) -> str:
    """
    Convert PDF pages to images with pdf2image then run pytesseract.
    Returns empty string if dependencies missing.
    Note: requires poppler & tesseract installed for full functionality.
    """
    if not convert_from_path or not pytesseract:
        return ""

    text_pieces = []
    try:
        images = convert_from_path(path, dpi=200)
        for img in images:
            try:
                piece = pytesseract.image_to_string(img)
            except Exception:
                piece = ""
            if piece:
                text_pieces.append(piece)
    except Exception:
        return ""

    return "\n".join(text_pieces).strip()

# -------------------------
# Summarization (lightweight)
# -------------------------
def summarize_text(text: str, n: int = 4) -> str:
    if not text or len(text.strip()) == 0:
        return "No readable content found."

    # Simple: return top n sentences by length/position heuristic
    sents = re.split(r'(?<=[.!?])\s+', text)
    if len(sents) <= n:
        return " ".join(sents).strip()
    # pick first n substantive sentences (skip tiny ones)
    chosen = []
    for s in sents:
        s = s.strip()
        if len(s) > 30:
            chosen.append(s)
        if len(chosen) >= n:
            break
    if not chosen:
        chosen = sents[:n]
    return " ".join(chosen).strip()

# -------------------------
# Improved Contract Type Detection
# -------------------------
def detect_contract_type(text: str) -> str:
    """
    Heuristic scoring:
      - Has 'judge', 'judgment', 'hon'ble' etc -> Court Judgment (strong override)
      - Otherwise we score several contract categories using keywords.
      - Return the label with highest score; if low confidence => General Legal Document.
    """
    t = (text or "").lower()

    # Quick override: detect court judgment / order
    judgment_signals = [
        "hon'ble", "hon’ble", "judgment", "judgement", "order", "judgment of",
        "court", "petitioner", "respondent", "appellant", "civil appeal",
        "scc", "supreme court", "high court", "bench"
    ]
    for k in judgment_signals:
        if k in t:
            return "Court Judgment / Order"

    # scoring map for contract types
    categories = {
        "Employment Contract": ["employee", "employer", "salary", "joining", "resignation", "notice period", "termination", "probation"],
        "Lease Agreement": ["lease", "tenant", "landlord", "rent", "premises", "let", "term of years", "security deposit"],
        "Non-Disclosure Agreement": ["non-disclosure", "confidential", "confidentiality", "nda", "proprietary information"],
        "Loan Agreement": ["loan", "borrower", "lender", "interest", "repayment", "installment", "security"],
        "Sales Agreement": ["seller", "buyer", "goods", "purchase", "delivery", "invoice", "sales agreement"],
        "Partnership Agreement": ["partnership", "partner", "capital contribution", "profit share", "partners"],
        "Service Agreement": ["services", "service provider", "scope of work", "deliverables", "service agreement", "statement of work"],
        "Franchise Agreement": ["franchise", "franchisor", "franchisee", "royalty"]
    }

    scores = {k: 0 for k in categories.keys()}
    for label, keywords in categories.items():
        for kw in keywords:
            # weight longer keyword phrases higher
            if kw in t:
                scores[label] += (3 if len(kw.split()) > 1 else 1)

    # pick top scoring label
    top_label = max(scores, key=lambda k: scores[k])
    top_score = scores[top_label]

    # confidence heuristics
    if top_score >= 3:
        return top_label
    if top_score > 0 and len(t) > 300:
        return top_label

    # fallback
    if len(t) < 200:
        return "Short Text / Unknown"
    return "General Legal Document"

# -------------------------
# Clause Detection (with excerpts)
# -------------------------
def detect_clauses_with_excerpts(text: str) -> dict:
    clauses = {
        "Confidentiality": ["confidential", "non-disclosure", "privacy", "proprietary"],
        "Termination": ["terminate", "termination", "expiry", "expire", "cancel"],
        "Payment": ["payment", "fee", "compensation", "remuneration", "invoice"],
        "Liability": ["liability", "liable", "damages", "responsible"],
        "Dispute Resolution": ["dispute", "arbitration", "mediation", "jurisdiction"],
        "Governing Law": ["governing law", "laws of", "jurisdiction"],
        "Intellectual Property": ["intellectual property", "copyright", "patent", "trademark", "ownership"],
        "Non-Compete": ["non-compete", "restrict", "competition", "restrictive covenant"],
        "Indemnity": ["indemnify", "indemnity", "hold harmless"],
        "Force Majeure": ["force majeure", "unforeseeable", "beyond control", "act of god"]
    }

    out = {}
    for cname, keys in clauses.items():
        found = False
        excerpt = ""
        for k in keys:
            pattern = re.compile(r'([^.]{0,300}\b' + re.escape(k) + r'\b[^.]{0,300})', re.IGNORECASE | re.DOTALL)
            m = pattern.search(text)
            if m:
                found = True
                excerpt_candidate = m.group(0).strip()
                excerpt = excerpt_candidate.replace("\n", " ").strip()
                break
        out[cname] = {"found": bool(found), "excerpt": excerpt}
    return out

# -------------------------
# Simple Entity Extraction
# -------------------------
def analyze_entities(text: str, limit: int = 40) -> str:
    if not text:
        return "No text"

    orgs = set(re.findall(r'\b[A-Z][A-Za-z0-9&\.,\s]{0,60}\b(?:Ltd|LLP|Pvt|Pvt\.|Limited|Inc|Corporation|Company|Bank)\b', text))
    people = set(re.findall(r'\b[A-Z][a-z]{2,}\s[A-Z][a-z]{2,}\b', text))
    dates = set(re.findall(r'\b\d{1,2}\s(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}\b', text))
    months = set(re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}\b', text))
    acts = set(re.findall(r'\b[A-Z][A-Za-z\s]{2,} Act(?: \d{4})?\b', text))

    parts = []
    if orgs:
        parts.append("Organizations: " + ", ".join(list(orgs)[:6]))
    if people:
        parts.append("People: " + ", ".join(list(people)[:8]))
    if dates:
        parts.append("Dates: " + ", ".join(list(dates)[:6]))
    elif months:
        parts.append("Dates: " + ", ".join(list(months)[:6]))
    if acts:
        parts.append("Acts: " + ", ".join(list(acts)[:6]))

    if not parts:
        return "No named entities found."
    return " | ".join(parts)

# -------------------------
# Risk Assessment
# -------------------------
def assess_risk(clause_map: dict) -> tuple:
    if not clause_map:
        return "Unknown", "No clause information available."

    total = len(clause_map)
    present = sum(1 for v in clause_map.values() if v.get("found"))
    ratio = (present / total) if total else 0

    if ratio >= 0.8:
        return "Low", "Most key clauses are present; minor legal review recommended."
    elif 0.5 <= ratio < 0.8:
        return "Medium", "Some important clauses are missing or incomplete — review recommended."
    else:
        return "High", "Multiple critical clauses missing — significant legal risk detected."

# -------------------------
# Document Version Comparison
# -------------------------
def compare_versions(text1: str, text2: str) -> float:
    if not text1 or not text2:
        return 0.0
    ratio = SequenceMatcher(None, text1, text2).ratio()
    return round(ratio * 100, 2)