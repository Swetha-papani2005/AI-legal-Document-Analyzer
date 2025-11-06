# ============================================================
# AI Legal Document Analyzer - Streamlit Dashboard
# With OCR support + Email Notifications + Activity Log
# ============================================================

import streamlit as st
import json
import os
from pathlib import Path
import hashlib
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import platform
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

# ✅ Windows Tesseract path (skip for Streamlit Cloud)
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ------------------ INITIAL SETUP ------------------
DATA_RAW = Path("../data/raw documents")
DATA_REPORTS = Path("../data/reports")
for path in [DATA_RAW, DATA_REPORTS]:
    path.mkdir(parents=True, exist_ok=True)

USERS_FILE = Path("users.json")
HISTORY_FILE = Path("history.json")
LOG_FILE = Path("activity_log.txt")
for f in [USERS_FILE, HISTORY_FILE]:
    if not f.exists():
        f.write_text("{}")

# ------------------ EMAIL CONFIG (Loaded Safely) ------------------
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASS = st.secrets["SENDER_PASS"]
ADMIN_EMAIL = st.secrets["ADMIN_EMAIL"]

def send_email_notification(subject, message):
    """Send notification email to admin securely"""
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = ADMIN_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.send_message(msg)
        print("✅ Email notification sent.")
    except Exception as e:
        print(f"⚠️ Email sending failed: {e}")

# ------------------ ACTIVITY LOG ------------------
def log_activity(action, email):
    """Store local activity log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {action} by {email}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

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

    # Notify + Log
    subject = "🆕 New User Registered on Legal Analyzer"
    message = f"A new user has registered.\n\nEmail: {email}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    send_email_notification(subject, message)
    log_activity("User Registered", email)
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
                # Notify + Log
                subject = "🔓 User Logged In - Legal Analyzer"
                message = f"User has logged in.\n\nEmail: {email}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                send_email_notification(subject, message)
                log_activity("User Logged In", email)
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

    if choice == "🚪 Logout":
        del st.session_state["user"]
        st.rerun()

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

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Words", len(text.split()))
                col2.metric("Characters", len(text))
                col3.metric("Sentences", text.count("."))
                col4.metric("Risk", risk_level)

                st.markdown("---")
                st.subheader("📘 Document Overview")
                st.write(f"Detected Type: {doc_type}")
                st.write(f"Risk Level: {risk_level}")
                st.info(risk_comment)
                st.subheader("🧠 Summary")
                st.success(summary)
                st.subheader("📜 Extracted Text")
                st.text_area("Full Document Text", text[:4000] + "...", height=250)

# ------------------ APP ENTRY ------------------
def main():
    st.set_page_config(page_title="AI Legal Document Analyzer", layout="wide")
    if "user" not in st.session_state:
        login_page()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()
