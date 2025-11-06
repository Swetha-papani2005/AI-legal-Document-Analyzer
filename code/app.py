# ============================================================
# AI Legal Document Analyzer - Streamlit Dashboard
# With OCR + Email Notifications + Activity Log + Strong Password + Reset Password
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


# ------------------ EMAIL CONFIG (SECURE) ------------------
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASS = st.secrets["SENDER_PASS"]
ADMIN_EMAIL = st.secrets["ADMIN_EMAIL"]


def send_email_notification(subject, message):
    """Send notification email securely"""
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
        print("✅ Email Sent")
    except Exception as e:
        print(f"⚠ Email Send Failed: {e}")


# ------------------ LOG ACTIVITY ------------------
def log_activity(action, email):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {action} by {email}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


# ------------------ PASSWORD UTILS ------------------
def strong_password(password):
    """Check password strength"""
    if len(password) < 8:
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for c in password):
        return False
    return True


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

    # Notify admin
    subject = "🆕 New User Registered"
    message = f"Email: {email}\nTime: {datetime.now()}"
    send_email_notification(subject, message)

    # Log
    log_activity("User Registered", email)
    return True


def reset_password(email, new_password):
    users = json.loads(USERS_FILE.read_text())

    if email not in users:
        return False

    users[email] = hash_password(new_password)
    USERS_FILE.write_text(json.dumps(users))

    # Notify admin
    subject = "🔁 Password Reset Performed"
    message = f"User reset password.\nEmail: {email}\nTime: {datetime.now()}"
    send_email_notification(subject, message)

    # Log
    log_activity("Password Reset", email)

    return True


# ------------------ OCR FUNCTION ------------------
def extract_text_with_ocr(pdf_path):
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
            <p>Login • Register • Reset Password</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Forgot Password"])

    # ---------------- LOGIN ----------------
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            if verify_user(email, password):
                st.session_state["user"] = email
                st.success("✅ Login successful!")

                # Email + Log
                subject = "🔓 User Logged In"
                message = f"Login by: {email}\nTime: {datetime.now()}"
                send_email_notification(subject, message)
                log_activity("User Logged In", email)

                st.rerun()
            else:
                st.error("❌ Incorrect email or password.")

    # ---------------- REGISTER ----------------
    with tab2:
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_pass")

        if st.button("Register"):
            if not strong_password(password):
                st.warning("⚠ Password must be 8+ chars, upper, lower, number, special char.")
            else:
                if register_user(email, password):
                    st.success("✅ Registration complete! Please login.")
                else:
                    st.error("⚠ Email already registered.")

    # ---------------- RESET PASSWORD ----------------
    with tab3:
        reset_email = st.text_input("Enter your registered email")
        new_pass = st.text_input("Enter new password", type="password")

        if st.button("Reset Password"):
            if not strong_password(new_pass):
                st.warning("⚠ Weak password. Use strong password.")
            else:
                if reset_password(reset_email, new_pass):
                    st.success("✅ Password reset successfully!")
                else:
                    st.error("❌ Email not found.")


# ------------------ SIDEBAR ------------------
def sidebar_nav():
    st.sidebar.markdown("<h2 class='sidebar-title'>⚖ Legal Analyzer</h2>", unsafe_allow_html=True)
    menu = ["📄 Analyze Document", "🔍 Compare Documents", "📊 Reports", "⚠ Risk Analysis", "🚪 Logout"]
    return st.sidebar.radio("Menu", menu)


# ------------------ SAVE HISTORY ------------------
def save_history(user, doc_type, risk, filename):
    history = json.loads(HISTORY_FILE.read_text())
    if user not in history:
        history[user] = []
    history[user].append({"file": filename, "type": doc_type, "risk": risk})
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


# ------------------ MAIN DASHBOARD ------------------
def main_dashboard():
    user = st.session_state["user"]
    choice = sidebar_nav()

    with open("styles.css") as css:
        st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

    st.markdown("<h1 class='title'>AI Legal Document Analyzer</h1>", unsafe_allow_html=True)

    if choice == "🚪 Logout":
        del st.session_state["user"]
        st.rerun()

    elif choice == "📄 Analyze Document":
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        manual_text = st.text_area("Or paste text", height=150)

        if uploaded_file or manual_text.strip():
            if uploaded_file:
                file_path = DATA_RAW / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                text = extract_text_from_pdf(str(file_path))
                if len(text) < 20:
                    st.warning("Scanned PDF detected — Running OCR...")
                    text = extract_text_with_ocr(str(file_path))
            else:
                text = manual_text

            if len(text) < 20:
                st.error("Could not extract readable text.")
                return

            st.success("✅ Document Processed!")

            # PROCESSING
            doc_type = detect_contract_type(text)
            clauses = detect_clauses_with_excerpts(text)
            risk_level, risk_comment = assess_risk(clauses)
            summary = summarize_text(text, n=4)

            save_history(user, doc_type, risk_level, uploaded_file.name if uploaded_file else "Manual Text")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Words", len(text.split()))
            col2.metric("Chars", len(text))
            col3.metric("Sentences", text.count("."))
            col4.metric("Risk", risk_level)

            st.subheader("📘 Overview")
            st.write("Type:", doc_type)
            st.write("Risk:", risk_level)
            st.info(risk_comment)

            st.subheader("🧠 Summary")
            st.success(summary)

            st.subheader("📜 Extracted Text")
            st.text_area("Text", text[:4000] + "...", height=250)


# ------------------ APP ENTRY ------------------
def main():
    st.set_page_config(page_title="AI Legal Document Analyzer", layout="wide")

    if "user" not in st.session_state:
        login_page()
    else:
        main_dashboard()


if __name__ == "__main__":
    main()
