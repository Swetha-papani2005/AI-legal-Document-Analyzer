# ============================================================
# AI Legal Document Analyzer - Streamlit Dashboard
# With OCR support (Windows + Streamlit Cloud)
# ============================================================

import streamlit as st
import json
import os
from pathlib import Path
import hashlib
from legal_core import (
    extract_text_from_pdf,
    summarize_text,
    detect_contract_type,
    detect_clauses_with_excerpts,
    assess_risk,
    compare_versions,
)

# OCR dependencies
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import platform

# ✅ Set Windows Tesseract path only if running locally (NOT on Streamlit Cloud)
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ------------------ INITIAL SETUP ------------------
DATA_RAW = Path("../data/raw documents")
DATA_REPORTS = Path("../data/reports")
for path in [DATA_RAW, DATA_REPORTS]:
    path.mkdir(parents=True, exist_ok=True)

USERS_FILE = Path("users.json")
HISTORY_FILE = Path("history.json")
for f in [USERS_FILE, HISTORY_FILE]:
    if not f.exists():
        f.write_text("{}")

# ------------------ PASSWORD UTILS ------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(email, password):
    users = json.loads(USERS_FILE.read_text())
    return email in users and users[email] == hash_password(password)

def register_user(email, password):
    users = json.loads(USERS_FILE.read_text())
    if email in users:
        return False
    users[email] = hash_password(password)
    USERS_FILE.write_text(json.dumps(users))
    return True

# ------------------ OCR FUNCTION ------------------
def extract_text_with_ocr(pdf_path):
    """Extracts text from scanned PDFs using OCR."""
    text = ""
    try:
        pages = convert_from_path(pdf_path, dpi=300)
        for page in pages:
            text += pytesseract.image_to_string(page, lang="eng")
    except Exception as e:
        st.error(f"OCR failed: {e}")
    return text.strip()

# ------------------ LOGIN PAGE ------------------
def login_page():
    st.markdown(
        """
        <div class="login-card">
            <h2>🔐 AI Legal Document Analyzer</h2>
            <p>Login or Register to continue</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if verify_user(email, password):
                st.session_state["user"] = email
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials.")

    with tab2:
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Register"):
            if register_user(email, password):
                st.success("✅ Account created! Please login.")
            else:
                st.error("⚠ Email already registered.")

# ------------------ SIDEBAR ------------------
def sidebar_nav():
    st.sidebar.markdown("<h2 class='sidebar-title'>⚖ Legal Analyzer Dashboard</h2>", unsafe_allow_html=True)
    menu = ["📄 Analyze Document", "🔍 Compare Documents", "📊 Reports", "⚠ Risk Analysis", "🚪 Logout"]
    choice = st.sidebar.radio("Navigate", menu, label_visibility="collapsed")

    st.sidebar.markdown("---")
    lang = st.sidebar.selectbox("🌐 Language", ["English", "Hindi", "Tamil", "Telugu"], key="lang_select")
    st.session_state["language"] = lang
    return choice

# ------------------ SAVE HISTORY ------------------
def save_history(user, doc_type, risk, filename):
    history = json.loads(HISTORY_FILE.read_text())
    if user not in history:
        history[user] = []
    entry = {"file": filename, "type": doc_type, "risk": risk}
    if entry not in history[user]:
        history[user].append(entry)
    HISTORY_FILE.write_text(json.dumps(history, indent=2))

# ------------------ MAIN DASHBOARD ------------------
def main_dashboard():
    user = st.session_state["user"]
    choice = sidebar_nav()

    with open("styles.css") as css:
        st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

    st.markdown("<h1 class='title'>AI Legal Document Analyzer</h1>", unsafe_allow_html=True)
    st.caption(f"Welcome, {user} | Smart Legal Insights in {st.session_state['language']}")

    # -------- Logout --------
    if choice == "🚪 Logout":
        del st.session_state["user"]
        st.rerun()

    # -------- Analyze Document --------
    elif choice == "📄 Analyze Document":
        uploaded_file = st.file_uploader("📂 Upload Legal Document (PDF)", type=["pdf"])
        manual_text = st.text_area("📝 Or Paste Document Text Here", height=150)

        if uploaded_file or manual_text.strip():
            if uploaded_file:
                file_path = DATA_RAW / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                text = extract_text_from_pdf(str(file_path))

                if not text or len(text) < 20:
                    st.warning("⚠ Detected scanned document — Running OCR...")
                    text = extract_text_with_ocr(str(file_path))
            else:
                text = manual_text

            if not text or len(text) < 20:
                st.error("❌ Could not extract readable text.")
            else:
                st.success("✅ Document successfully processed!")

                doc_type = detect_contract_type(text)
                clauses = detect_clauses_with_excerpts(text)
                risk_level, risk_comment = assess_risk(clauses)
                summary = summarize_text(text, n=4)

                save_history(user, doc_type, risk_level, uploaded_file.name if uploaded_file else "Manual Text")

                word_count = len(text.split())
                char_count = len(text)
                sentence_count = text.count(".")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Words", word_count)
                col2.metric("Characters", char_count)
                col3.metric("Sentences", sentence_count)
                col4.metric("Risk", risk_level)

                st.markdown("---")
                st.subheader("📘 Document Overview")
                st.write(f"Detected Type: {doc_type}")
                st.write(f"Risk Level: {risk_level}")
                st.info(risk_comment)
                st.subheader("🧠 Summary")
                st.success(summary)

                st.subheader("📑 Key Clauses Found")
                st.markdown("""
                <style>
                .clause-box {
                    background-color: #f9f9ff;
                    border-left: 5px solid #919dee;
                    padding: 10px 15px;
                    border-radius: 8px;
                    margin-bottom: 10px;
                }
                .clause-title {
                    font-weight: 600;
                    color: #2b2b2b;
                }
                .clause-status {
                    float: right;
                    font-weight: bold;
                }
                .found {
                    color: #008000;
                }
                .missing {
                    color: #e63946;
                }
                </style>
                """, unsafe_allow_html=True)

                for clause, info in clauses.items():
                    status_icon = "✅" if info["found"] else "❌"
                    status_class = "found" if info["found"] else "missing"
                    excerpt = info["excerpt"][:200] + "..." if info["found"] and info["excerpt"] else ""
                    st.markdown(
                        f"""
                        <div class="clause-box">
                            <span class="clause-title">{clause}</span>
                            <span class="clause-status {status_class}">{status_icon} {'Found' if info['found'] else 'Missing'}</span>
                            <br>
                            <small>{excerpt}</small>
                        </div>
                        """, unsafe_allow_html=True)

                st.subheader("📜 Extracted Text")
                st.text_area("Full Document Text", text[:4000] + "...", height=250)

    # -------- Compare Documents --------
    elif choice == "🔍 Compare Documents":
        col1, col2 = st.columns(2)
        file1 = col1.file_uploader("Upload First Document", type=["pdf"], key="cmp1")
        file2 = col2.file_uploader("Upload Second Document", type=["pdf"], key="cmp2")
        if file1 and file2:
            p1 = DATA_RAW / file1.name
            p2 = DATA_RAW / file2.name
            with open(p1, "wb") as f:
                f.write(file1.getbuffer())
            with open(p2, "wb") as f:
                f.write(file2.getbuffer())
            t1 = extract_text_from_pdf(str(p1))
            t2 = extract_text_from_pdf(str(p2))
            sim = compare_versions(t1, t2)
            st.metric("Similarity", f"{sim}%")

            if sim > 80:
                st.success("✅ Documents are very similar.")
            elif sim > 50:
                st.warning("⚠ Moderate differences found.")
            else:
                st.error("❌ Significant differences detected.")

    # -------- Reports --------
    elif choice == "📊 Reports":
        st.subheader("📊 Document Analysis Reports")
        history = json.loads(HISTORY_FILE.read_text())
        user_history = history.get(user, [])
        if not user_history:
            st.info("No reports available yet.")
        else:
            for item in user_history:
                st.markdown(f"📄 {item['file']} → Type: {item['type']} | Risk: {item['risk']}")

    # -------- Risk Analysis --------
    elif choice == "⚠ Risk Analysis":
        st.subheader("⚠ Risk Level Overview")
        history = json.loads(HISTORY_FILE.read_text())
        user_history = history.get(user, [])

        if not user_history:
            st.info("No analyzed documents yet.")
        else:
            low = [d for d in user_history if d["risk"] == "Low"]
            med = [d for d in user_history if d["risk"] == "Medium"]
            high = [d for d in user_history if d["risk"] == "High"]
            st.write(f"🟢 Low Risk: {len(low)} documents")
            st.write(f"🟡 Medium Risk: {len(med)} documents")
            st.write(f"🔴 High Risk: {len(high)} documents")

            if st.button("🗑 Clear History"):
                history[user] = []
                HISTORY_FILE.write_text(json.dumps(history, indent=2))
                st.success("✅ History cleared!")
                st.rerun()

# ------------------ APP ENTRY ------------------
def main():
    st.set_page_config(page_title="AI Legal Document Analyzer", layout="wide")
    if "user" not in st.session_state:
        login_page()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()
