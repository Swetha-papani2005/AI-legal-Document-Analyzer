# ============================================================
# AI Legal Document Analyzer - Streamlit Dashboard
# With OCR + Email Notifications + Activity Log + Strong Password + Reset Password
# ============================================================

import streamlit as st
import json
from pathlib import Path
import hashlib
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import platform

from legal_core import (
    extract_text_from_pdf,
    summarize_text,
    detect_contract_type,
    detect_clauses_with_excerpts,
    assess_risk,
    compare_versions,
)

# OCR
from pdf2image import convert_from_path
import pytesseract
from PIL import Image


# ✅ Windows Tesseract Path
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ------------------ INITIAL SETUP ------------------
DATA_RAW = Path("../data/raw documents")
DATA_REPORTS = Path("../data/reports")
for p in [DATA_RAW, DATA_REPORTS]:
    p.mkdir(parents=True, exist_ok=True)

USERS_FILE = Path("users.json")
HISTORY_FILE = Path("history.json")
LOG_FILE = Path("activity_log.txt")

for f in [USERS_FILE, HISTORY_FILE]:
    if not f.exists():
        f.write_text("{}")


# ------------------ EMAIL CONFIG ------------------
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASS = st.secrets["SENDER_PASS"]
ADMIN_EMAIL = st.secrets["ADMIN_EMAIL"]

def send_email(to_email, subject, content):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(content, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email Error:", e)


def notify_admin(subject, content):
    send_email(ADMIN_EMAIL, subject, content)


# ------------------ ACTIVITY LOG ------------------
def log_activity(action, user):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {action} by {user}\n"
    with open(LOG_FILE, "a") as f:
        f.write(entry)


# ------------------ PASSWORD MANAGEMENT ------------------
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()


def strong_password(p):
    return (
        len(p) >= 8
        and any(c.isupper() for c in p)
        and any(c.islower() for c in p)
        and any(c.isdigit() for c in p)
        and any(c in "!@#$%^&*()_+-=<>?" for c in p)
    )


def verify_user(email, password):
    users = json.loads(USERS_FILE.read_text())
    return email in users and users[email] == hash_password(password)


def register_user(email, password):
    users = json.loads(USERS_FILE.read_text())
    if email in users:
        return False
    users[email] = hash_password(password)
    USERS_FILE.write_text(json.dumps(users))

    notify_admin("🆕 New User Registered", f"User: {email}")
    log_activity("User Registered", email)
    return True


# ------------------ OTP SYSTEM ------------------
OTP_STORE = {}

def generate_otp():
    return "".join(random.choices(string.digits, k=6))


# ------------------ OCR FUNCTION ------------------
def extract_text_with_ocr(path):
    text = ""
    try:
        pages = convert_from_path(path, dpi=300)
        for page in pages:
            text += pytesseract.image_to_string(page)
    except Exception as e:
        st.error(f"OCR Failed: {e}")
    return text


# ------------------ LOGIN PAGE ------------------
def login_page():
    st.markdown("<h2>🔐 AI Legal Document Analyzer</h2>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Forgot Password"])

    # ------------------ LOGIN ------------------
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if verify_user(email, password):
                st.session_state["user"] = email
                notify_admin("🔓 User Logged In", f"User: {email}")
                log_activity("Login", email)
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid email or password")

    # ------------------ REGISTER ------------------
    with tab2:
        email = st.text_input("New Email")
        password = st.text_input("Create Password", type="password")

        if st.button("Register"):
            if not strong_password(password):
                st.error("❌ Weak password! Use 8+ chars, upper, lower, number, special symbol.")
            else:
                if register_user(email, password):
                    st.success("Account created! Please login.")
                else:
                    st.error("Email already registered.")

    # ------------------ FORGOT PASSWORD ------------------
    with tab3:
        email_fp = st.text_input("Enter Email for Password Reset")
        if st.button("Send OTP"):
            otp = generate_otp()
            OTP_STORE[email_fp] = otp
            send_email(email_fp, "Your Password Reset OTP", f"Your OTP is: {otp}")
            st.success("OTP sent to your email!")

        otp_entered = st.text_input("Enter OTP")
        new_pass = st.text_input("New Password", type="password")

        if st.button("Reset Password"):
            if email_fp in OTP_STORE and OTP_STORE[email_fp] == otp_entered:
                if not strong_password(new_pass):
                    st.error("Weak password!")
                else:
                    users = json.loads(USERS_FILE.read_text())
                    users[email_fp] = hash_password(new_pass)
                    USERS_FILE.write_text(json.dumps(users))
                    st.success("Password reset successful!")
            else:
                st.error("Invalid OTP")


# ------------------ SIDEBAR ------------------
def sidebar():
    st.sidebar.title("⚖ Legal Analyzer")
    return st.sidebar.radio("Menu", ["Analyze Document", "Compare Documents", "Reports", "Risk Analysis", "Logout"])


# ------------------ MAIN DASHBOARD ------------------
def main_dashboard():
    user = st.session_state["user"]
    choice = sidebar()

    st.write(f"Welcome, **{user}**")

    # -------- Logout --------
    if choice == "Logout":
        del st.session_state["user"]
        st.rerun()

    # -------- Analyze Document --------
    if choice == "Analyze Document":
        uploaded = st.file_uploader("Upload PDF", type=["pdf"])
        text_box = st.text_area("Or paste text")

        if uploaded:
            path = DATA_RAW / uploaded.name
            with open(path, "wb") as f:
                f.write(uploaded.getbuffer())

            text = extract_text_from_pdf(str(path))
            if len(text) < 20:
                st.warning("Scanned file detected — running OCR")
                text = extract_text_with_ocr(str(path))
        else:
            text = text_box

        if text:
            st.success("Document processed!")

            doc_type = detect_contract_type(text)
            clauses = detect_clauses_with_excerpts(text)
            risk, comment = assess_risk(clauses)
            summary = summarize_text(text)

            # ---------- SUMMARY ----------
            st.subheader("🧠 Summary")
            st.info(summary)

            # ---------- KEY CLAUSES ----------
            st.subheader("📑 Key Clauses Found")

            st.markdown("""
            <style>
            .clause-box {
                background-color: #f9f9ff;
                border-left: 5px solid #919dee;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 10px;
            }
            .found { color: green; font-weight: bold; }
            .missing { color: red; font-weight: bold; }
            </style>
            """, unsafe_allow_html=True)

            for c, info in clauses.items():
                icon = "✅" if info["found"] else "❌"
                cls = "found" if info["found"] else "missing"
                excerpt = info["excerpt"][:200] + "..." if info["found"] else ""

                st.markdown(
                    f"""
                    <div class='clause-box'>
                        <span class='{cls}'>{icon} {c}</span><br>
                        <small>{excerpt}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # ---------- EXTRACTED TEXT ----------
            st.subheader("📜 Extracted Text")
            st.text_area("Text", text[:4000] + "...", height=200)

    # -------- Compare Documents --------
    if choice == "Compare Documents":
        f1 = st.file_uploader("Upload Document 1", type=["pdf"])
        f2 = st.file_uploader("Upload Document 2", type=["pdf"])

        if f1 and f2:
            p1 = DATA_RAW / f1.name
            p2 = DATA_RAW / f2.name
            open(p1, "wb").write(f1.getbuffer())
            open(p2, "wb").write(f2.getbuffer())

            t1 = extract_text_from_pdf(str(p1))
            t2 = extract_text_from_pdf(str(p2))

            score = compare_versions(t1, t2)
            st.metric("Similarity", f"{score}%")


# ------------------ APP ENTRY ------------------
def main():
    st.set_page_config(page_title="AI Legal Analyzer", layout="wide")

    if "user" not in st.session_state:
        login_page()
    else:
        main_dashboard()


if __name__ == "__main__":
    main()
