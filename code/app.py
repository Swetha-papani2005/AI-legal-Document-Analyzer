# ============================================================
# AI Legal Document Analyzer - Streamlit Dashboard
# ============================================================

import streamlit as st
st.set_page_config(page_title="AI Legal Document Analyzer", layout="wide")

import json, hashlib, os
from pathlib import Path
from legal_core import (
    extract_text_from_pdf,
    summarize_text,
    detect_contract_type,
    detect_clauses_with_excerpts,
    assess_risk,
    compare_versions
)

from PyPDF2 import PdfReader
import pytesseract, pypdfium2

# ✅ Tesseract OCR path
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ✅ Check if PDF has text
def pdf_has_text(path):
    try:
        r = PdfReader(path)
        for p in r.pages:
            if p.extract_text():
                return True
        return False
    except:
        return True

# ✅ OCR (no Poppler)
def extract_text_with_ocr(pdf_path):
    text = ""
    try:
        pdf = pypdfium2.PdfDocument(pdf_path)
        for i in range(len(pdf)):
            page = pdf.get_page(i)
            img = page.render(scale=3).to_pil()
            text += pytesseract.image_to_string(img, lang="eng")
            page.close()
        pdf.close()
    except Exception as e:
        st.error(f"OCR failed: {e}")
    return text.strip()

# ✅ Data folders
DATA_RAW = Path("../data/raw documents")
DATA_REPORTS = Path("../data/reports")
for x in [DATA_RAW, DATA_REPORTS]: x.mkdir(parents=True, exist_ok=True)

USERS_FILE, HISTORY_FILE = Path("users.json"), Path("history.json")
if not USERS_FILE.exists(): USERS_FILE.write_text("{}")
if not HISTORY_FILE.exists(): HISTORY_FILE.write_text("{}")

# ✅ Auth
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def verify_user(e,p): 
    u = json.loads(USERS_FILE.read_text())
    return e in u and u[e] == hash_password(p)
def register_user(e,p):
    u = json.loads(USERS_FILE.read_text())
    if e in u: return False
    u[e] = hash_password(p); USERS_FILE.write_text(json.dumps(u)); return True

# ✅ Login Page
def login_page():
    st.markdown("""
    <div class="login-card">
        <h2>🔐 AI Legal Document Analyzer</h2>
        <p>Login or Register to continue</p>
    </div>
    """, unsafe_allow_html=True)

    l,r = st.tabs(["Login","Register"])

    with l:
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            if verify_user(email,pw):
                st.session_state.user = email
                st.success("✅ Login successful!")
                st.rerun()
            else: st.error("❌ Invalid credentials")

    with r:
        email = st.text_input("Email ", key="re")
        pw = st.text_input("Password ", type="password", key="rp")
        if st.button("Register"):
            if register_user(email,pw): st.success("✅ Registered! Login now")
            else: st.error("⚠ Email already exists")

# ✅ Sidebar
def sidebar_nav():
    st.sidebar.markdown("<h2 class='sidebar-title'>⚖ Legal Analyzer Dashboard</h2>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Menu",["📄 Analyze Document","🔍 Compare Documents","📊 Reports","⚠ Risk Analysis","🚪 Logout"])
    st.sidebar.write("---")
    st.sidebar.selectbox("🌐 Language",["English","Hindi","Tamil","Telugu"])
    return menu

# ✅ Save history
def save_history(u,t,r,f):
    h=json.loads(HISTORY_FILE.read_text())
    if u not in h: h[u]=[]
    x={"file":f,"type":t,"risk":r}
    if x not in h[u]: h[u].append(x)
    HISTORY_FILE.write_text(json.dumps(h,indent=2))

# ✅ Dashboard
def main_dashboard():
    u = st.session_state.user
    choice = sidebar_nav()
    with open("styles.css") as f: st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown("<h1 class='title'>AI Legal Document Analyzer</h1>", unsafe_allow_html=True)
    st.caption(f"Welcome, {u}")

    if choice == "🚪 Logout":
        del st.session_state.user
        st.rerun()

    # --------- ANALYZE DOCUMENT ---------
    if choice == "📄 Analyze Document":
        file = st.file_uploader("📂 Upload Legal Document (PDF)", type=["pdf"])
        manual = st.text_area("📝 Or Paste Document Text Here", height=150)

        if file or manual.strip():

            if file:
                path = DATA_RAW / file.name
                open(path,"wb").write(file.getbuffer())

                if pdf_has_text(str(path)):
                    text = extract_text_from_pdf(str(path))
                else:
                    st.warning("⚠ Detected a scanned document. Applying OCR extraction...")
                    text = extract_text_with_ocr(str(path))
            else:
                text = manual

            if not text.strip(): st.error("❌ Unable to extract text"); return

            st.success("✅ Document successfully processed!")

            doc = detect_contract_type(text)
            clauses = detect_clauses_with_excerpts(text)
            risk, risk_msg = assess_risk(clauses)
            summary = summarize_text(text, n=4)

            save_history(u,doc,risk,file.name if file else "Manual Text")

            # ✅ METRICS (Words, Characters, Sentences, Risk)
            word_count = len(text.split())
            char_count = len(text)
            sentence_count = text.count(".") + text.count("?") + text.count("!")

            st.markdown("""
            <style>
            .metric-box{background:#fff;padding:18px;border-radius:12px;text-align:center;
            border:2px solid #e0e7ff;box-shadow:0px 2px 8px rgba(0,0,0,0.06);}
            .metric-value{font-size:28px;font-weight:800;color:#7a8df5;}
            .metric-label{font-size:14px;font-weight:600;color:#333;}
            </style>""", unsafe_allow_html=True)

            c1,c2,c3,c4 = st.columns(4)
            c1.markdown(f"<div class='metric-box'><div class='metric-value'>{word_count}</div><div class='metric-label'>Words</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-box'><div class='metric-value'>{char_count}</div><div class='metric-label'>Characters</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-box'><div class='metric-value'>{sentence_count}</div><div class='metric-label'>Sentences</div></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='metric-box'><div class='metric-value'>{risk}</div><div class='metric-label'>Risk</div></div>", unsafe_allow_html=True)

            st.subheader("📘 Document Overview")
            st.write(f"Detected Type: **{doc}**")
            st.info(risk_msg)
            st.subheader("🧠 Summary")
            st.success(summary)

            # ✅ KEY CLAUSES UI (exact as screenshot)
            st.subheader("📑 Key Clauses Found")

            st.markdown("""
            <style>
            .clause-box{background:#f9f9ff;border-left:6px solid #7a8df5;border-radius:10px;
            padding:12px 18px;margin-bottom:10px;box-shadow:0 2px 5px rgba(0,0,0,0.05);}
            .clause-title{font-size:16px;font-weight:700;}
            .status{float:right;font-weight:700;}
            .found{color:#0a8f0a;} .missing{color:#c0392b;}
            .excerpt{font-size:14px;color:#555;margin-top:3px;}
            </style>""", unsafe_allow_html=True)

            for clause,info in clauses.items():
                status = "✅ Found" if info["found"] else "❌ Missing"
                cls = "found" if info["found"] else "missing"
                excerpt = info["excerpt"][:200]+"..." if info["excerpt"] else ""
                st.markdown(f"""
                <div class="clause-box">
                    <span class="clause-title">{clause}</span>
                    <span class="status {cls}">{status}</span><br>
                    <span class="excerpt">{excerpt}</span>
                </div>
                """, unsafe_allow_html=True)

            st.subheader("📜 Extracted Text")
            st.text_area("Full Text", text[:5000]+"...", height=250)

    # --------- COMPARE ---------
    elif choice=="🔍 Compare Documents":
        c1,c2=st.columns(2)
        f1=c1.file_uploader("First PDF",type=["pdf"])
        f2=c2.file_uploader("Second PDF",type=["pdf"])
        if f1 and f2:
            p1,p2 = DATA_RAW/f1.name, DATA_RAW/f2.name
            open(p1,"wb").write(f1.getbuffer()); open(p2,"wb").write(f2.getbuffer())
            sim = compare_versions(extract_text_from_pdf(p1),extract_text_from_pdf(p2))
            st.metric("Similarity", f"{sim}%")

    # --------- REPORTS ---------
    elif choice=="📊 Reports":
        h=json.loads(HISTORY_FILE.read_text()).get(u,[])
        if not h: st.info("No history yet.")
        for x in h: st.write(f"📄 {x['file']} → {x['type']} | Risk: {x['risk']}")

    # --------- RISK ANALYSIS ---------
    elif choice=="⚠ Risk Analysis":
        h=json.loads(HISTORY_FILE.read_text()).get(u,[])
        low=len([x for x in h if x["risk"]=="Low"])
        med=len([x for x in h if x["risk"]=="Medium"])
        high=len([x for x in h if x["risk"]=="High"])
        st.write(f"🟢 Low Risk: {low}")
        st.write(f"🟡 Medium Risk: {med}")
        st.write(f"🔴 High Risk: {high}")
        if st.button("🗑 Clear History"):
            json.dump({},open(HISTORY_FILE,"w"))
            st.success("✅ History Cleared!"); st.rerun()

def main():
    if "user" not in st.session_state: login_page()
    else: main_dashboard()

if __name__=="__main__": main()
