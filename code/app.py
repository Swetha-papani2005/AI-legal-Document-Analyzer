# ============================================================
# AI Legal Document Analyzer - Streamlit Dashboard
# OCR + Email Notifications + Activity Log
# Strong Passwords + Reset Password
# Key Clauses (Found & Missing) + Reports + Risk + Compare
# ============================================================

import streamlit as st
import json, os, hashlib, platform, smtplib
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from legal_core import (
    extract_text_from_pdf,
    summarize_text,
    detect_contract_type,
    detect_clauses_with_excerpts,
    assess_risk,
    compare_versions,
)

# OCR deps
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# ---------- Page config ----------
st.set_page_config(page_title="AI Legal Document Analyzer", layout="wide")

# ---------- Windows-only Tesseract path (skip on Streamlit Cloud) ----------
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ---------- Storage setup ----------
DATA_RAW = Path("../data/raw documents")
DATA_REPORTS = Path("../data/reports")
for p in (DATA_RAW, DATA_REPORTS):
    p.mkdir(parents=True, exist_ok=True)

USERS_FILE = Path("users.json")
HISTORY_FILE = Path("history.json")
LOG_FILE = Path("activity_log.txt")

if not USERS_FILE.exists():
    USERS_FILE.write_text("{}")
if not HISTORY_FILE.exists():
    HISTORY_FILE.write_text("{}")

# ---------- Email secrets ----------
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASS  = st.secrets["SENDER_PASS"]
ADMIN_EMAIL  = st.secrets["ADMIN_EMAIL"]

def send_email_notification(subject: str, message: str):
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
    except Exception as e:
        print(f"Email send failed: {e}")

# ---------- Logging ----------
def log_activity(action: str, email: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {action} by {email}\n")

# ---------- Password utils ----------
def strong_password(pw: str) -> bool:
    if len(pw) < 8: return False
    if not any(c.islower() for c in pw): return False
    if not any(c.isupper() for c in pw): return False
    if not any(c.isdigit() for c in pw): return False
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/\\\"" for c in pw): return False
    return True

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_user(email: str, pw: str) -> bool:
    users = json.loads(USERS_FILE.read_text())
    return email in users and users[email] == hash_password(pw)

def register_user(email: str, pw: str) -> bool:
    users = json.loads(USERS_FILE.read_text())
    if email in users:
        return False
    users[email] = hash_password(pw)
    USERS_FILE.write_text(json.dumps(users, indent=2))
    send_email_notification("🆕 New User Registered",
                            f"Email: {email}\nTime: {datetime.now()}")
    log_activity("User Registered", email)
    return True

def reset_password(email: str, new_pw: str) -> bool:
    users = json.loads(USERS_FILE.read_text())
    if email not in users:
        return False
    users[email] = hash_password(new_pw)
    USERS_FILE.write_text(json.dumps(users, indent=2))
    send_email_notification("🔁 Password Reset",
                            f"Email: {email}\nTime: {datetime.now()}")
    log_activity("Password Reset", email)
    return True

# ---------- OCR ----------
def extract_text_with_ocr(pdf_path: str) -> str:
    text = ""
    try:
        pages = convert_from_path(pdf_path, dpi=300)
        for page in pages:
            text += pytesseract.image_to_string(page, lang="eng")
    except Exception as e:
        st.error(f"OCR failed: {e}")
    return text.strip()

# ---------- Auth screens ----------
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
    tab_login, tab_reg, tab_reset = st.tabs(["Login", "Register", "Forgot Password"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        pw    = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            if verify_user(email, pw):
                st.session_state["user"] = email
                send_email_notification("🔓 User Logged In",
                                        f"Email: {email}\nTime: {datetime.now()}")
                log_activity("User Logged In", email)
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Incorrect email or password.")

    with tab_reg:
        email = st.text_input("Email", key="reg_email")
        pw    = st.text_input("Password", type="password", key="reg_pw")
        if st.button("Register"):
            if not strong_password(pw):
                st.warning("Password must be 8+ chars with upper, lower, digit, special char.")
            else:
                if register_user(email, pw):
                    st.success("Registered! Please login.")
                else:
                    st.error("Email already registered.")

    with tab_reset:
        email = st.text_input("Registered Email", key="reset_email")
        pw    = st.text_input("New Password", type="password", key="reset_pw")
        if st.button("Reset Password"):
            if not strong_password(pw):
                st.warning("Weak password. Use upper/lower/digit/special and 8+ length.")
            else:
                if reset_password(email, pw):
                    st.success("Password reset successful!")
                else:
                    st.error("Email not found.")

# ---------- Sidebar ----------
def sidebar_nav():
    st.sidebar.markdown("<h2 class='sidebar-title'>⚖ Legal Analyzer</h2>", unsafe_allow_html=True)
    menu = ["📄 Analyze Document", "🔍 Compare Documents", "📊 Reports", "⚠ Risk Analysis", "🚪 Logout"]
    return st.sidebar.radio("Menu", menu, label_visibility="collapsed")

# ---------- History ----------
def save_history(user: str, doc_type: str, risk: str, filename: str):
    history = json.loads(HISTORY_FILE.read_text())
    if user not in history:
        history[user] = []
    entry = {"file": filename, "type": doc_type, "risk": risk}
    history[user].append(entry)
    HISTORY_FILE.write_text(json.dumps(history, indent=2))

# ---------- Main app ----------
def main_dashboard():
    user = st.session_state["user"]
    choice = sidebar_nav()

    # Load styles if present
    if Path("styles.css").exists():
        with open("styles.css") as css:
            st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

    st.markdown("<h1 class='title'>AI Legal Document Analyzer</h1>", unsafe_allow_html=True)

    # --- Logout ---
    if choice == "🚪 Logout":
        del st.session_state["user"]
        st.rerun()

    # --- Analyze Document ---
    elif choice == "📄 Analyze Document":
        uploaded = st.file_uploader("Upload PDF", type=["pdf"])
        manual_text = st.text_area("Or paste text here", height=150)

        if uploaded or manual_text.strip():
            if uploaded:
                pdf_path = DATA_RAW / uploaded.name
                with open(pdf_path, "wb") as f:
                    f.write(uploaded.getbuffer())
                text = extract_text_from_pdf(str(pdf_path))
                if len(text) < 20:
                    st.warning("Scanned PDF detected — running OCR…")
                    text = extract_text_with_ocr(str(pdf_path))
            else:
                text = manual_text

            if len(text) < 20:
                st.error("Could not extract readable text.")
                return

            st.success("✅ Document processed!")

            # Core analysis
            doc_type = detect_contract_type(text)
            clauses  = detect_clauses_with_excerpts(text)     # expects {clause: {"found":bool, "excerpt":str}}
            risk_level, risk_comment = assess_risk(clauses)
            summary  = summarize_text(text, n=4)

            save_history(user, doc_type, risk_level, uploaded.name if uploaded else "Manual Text")

            # Metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Words", len(text.split()))
            c2.metric("Characters", len(text))
            c3.metric("Sentences", text.count("."))
            c4.metric("Risk", risk_level)

            # Overview
            st.subheader("📘 Overview")
            st.write("Type:", doc_type)
            st.write("Risk:", risk_level)
            st.info(risk_comment)

            # Summary
            st.subheader("🧠 Summary")
            st.success(summary)

            # ---------- Key Clauses (Found + Missing) ----------
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
            .clause-title { font-weight: 600; color: #2b2b2b; }
            .clause-status { float: right; font-weight: bold; }
            .found { color: #008000; }
            .missing { color: #e63946; }
            </style>
            """, unsafe_allow_html=True)

            for clause, info in clauses.items():
                status_icon  = "✅" if info.get("found") else "❌"
                status_class = "found" if info.get("found") else "missing"
                excerpt = (info.get("excerpt") or "")
                excerpt = (excerpt[:200] + "...") if (info.get("found") and excerpt) else ""
                st.markdown(
                    f"""
                    <div class="clause-box">
                        <span class="clause-title">{clause}</span>
                        <span class="clause-status {status_class}">
                            {status_icon} {'Found' if info.get('found') else 'Missing'}
                        </span><br>
                        <small>{excerpt}</small>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # Extracted text preview
            st.subheader("📜 Extracted Text")
            st.text_area("Text", text[:4000] + ("..." if len(text) > 4000 else ""), height=250)

    # --- Compare Documents ---
    elif choice == "🔍 Compare Documents":
        st.subheader("🔍 Compare Two Documents")
        col1, col2 = st.columns(2)
        f1 = col1.file_uploader("Upload First Document", type=["pdf"], key="cmp1")
        f2 = col2.file_uploader("Upload Second Document", type=["pdf"], key="cmp2")

        if f1 and f2:
            p1 = DATA_RAW / f1.name
            p2 = DATA_RAW / f2.name
            with open(p1, "wb") as f: f.write(f1.getbuffer())
            with open(p2, "wb") as f: f.write(f2.getbuffer())
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

    # --- Reports ---
    elif choice == "📊 Reports":
        st.subheader("📊 Analysis Reports")
        history = json.loads(HISTORY_FILE.read_text())
        user_history = history.get(user, [])
        if not user_history:
            st.info("No reports yet.")
        else:
            for item in user_history:
                st.markdown(f"📄 **{item['file']}** — Type: **{item['type']}**, Risk: **{item['risk']}**")

    # --- Risk Analysis ---
    elif choice == "⚠ Risk Analysis":
        st.subheader("⚠ Risk Level Overview")
        history = json.loads(HISTORY_FILE.read_text())
        user_history = history.get(user, [])
        if not user_history:
            st.info("No analyzed documents yet.")
        else:
            low  = [d for d in user_history if d["risk"] == "Low"]
            med  = [d for d in user_history if d["risk"] == "Medium"]
            high = [d for d in user_history if d["risk"] == "High"]
            st.write(f"🟢 Low Risk: {len(low)}")
            st.write(f"🟡 Medium Risk: {len(med)}")
            st.write(f"🔴 High Risk: {len(high)}")

# ---------- Entry ----------
def main():
    if "user" not in st.session_state:
        login_page()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()
