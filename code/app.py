# ============================================================
# AI Legal Document Analyzer - Streamlit Dashboard
# With OCR + Email Notifications + Secure Secrets + Activity Log
# ============================================================

import streamlit as st
import json
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

# OCR
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


# ------------------ EMAIL CONFIG (SECURE SECRETS) ------------------
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASS = st.secrets["SENDER_PASS"]
ADMIN_EMAIL = st.secrets["ADMIN_EMAIL"]

def send_email_notification(subject, message):
    """Send email to admin"""
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

        print("✅ Email sent!")
    except Exception as e:
        print("Email failed:", e)


# ------------------ LOGGING ------------------
def log_activity(action, email):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {action} by {email}\n")


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
    
    if len(password) < 6:
        return "weak"

    users[email] = hash_password(password)
    USERS_FILE.write_text(json.dumps(users))

    # Notifications
    send_email_notification(
        "🆕 New User Registered",
        f"New user registered:\nEmail: {email}\nTime: {datetime.now()}"
    )
    log_activity("User Registered", email)
    return True


def reset_password(email, new_password):
    users = json.loads(USERS_FILE.read_text())
    users[email] = hash_password(new_password)
    USERS_FILE.write_text(json.dumps(users))

    send_email_notification(
        "🔑 Password Reset",
        f"User reset password:\nEmail: {email}\nTime: {datetime.now()}"
    )
    log_activity("Password Reset", email)


# ------------------ OCR FUNCTION ------------------
def extract_text_with_ocr(pdf_path):
    text = ""
    try:
        pages = convert_from_path(pdf_path, dpi=300)
        for page in pages:
            text += pytesseract.image_to_string(page, lang="eng")
    except Exception as e:
        st.error("OCR failed:", e)
    return text.strip()


# ------------------ LOGIN PAGE ------------------
def login_page():
    st.markdown("<h2>🔐 AI Legal Document Analyzer</h2>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Reset Password"])

    # LOGIN
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if verify_user(email, password):
                st.session_state["user"] = email

                send_email_notification(
                    "✅ User Logged In",
                    f"Email: {email}\nTime: {datetime.now()}"
                )
                log_activity("User Logged In", email)
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

    # REGISTER
    with tab2:
        email = st.text_input("Register Email")
        password = st.text_input("Create Password", type="password")

        if st.button("Register"):
            result = register_user(email, password)

            if result == "weak":
                st.error("⚠ Password must be at least 6 characters.")
            elif result:
                st.success("✅ Registered Successfully!")
            else:
                st.error("⚠ Email already exists!")

    # RESET PASSWORD
    with tab3:
        email = st.text_input("Email for Reset")
        new_password = st.text_input("New Password", type="password")

        if st.button("Reset Password"):
            reset_password(email, new_password)
            st.success("✅ Password Reset Successfully!")


# ------------------ SIDEBAR ------------------
def sidebar_nav():
    menu = ["📄 Analyze Document", "🔍 Compare Documents", "📊 Reports", "⚠ Risk Analysis", "🚪 Logout"]
    return st.sidebar.radio("Menu", menu)


# ------------------ SAVE HISTORY ------------------
def save_history(user, doc_type, risk, filename):
    history = json.loads(HISTORY_FILE.read_text())

    if user not in history:
        history[user] = []

    entry = {"file": filename, "type": doc_type, "risk": risk}
    history[user].append(entry)

    HISTORY_FILE.write_text(json.dumps(history, indent=2))


# ------------------ MAIN DASHBOARD ------------------
def main_dashboard():
    user = st.session_state["user"]
    choice = sidebar_nav()

    st.markdown(f"<h2>Welcome, {user}</h2>", unsafe_allow_html=True)

    # LOGOUT
    if choice == "🚪 Logout":
        del st.session_state["user"]
        st.rerun()

    # ANALYZE DOCUMENT
    elif choice == "📄 Analyze Document":
        uploaded = st.file_uploader("Upload PDF", type=["pdf"])
        text_input = st.text_area("Or paste text here")

        if uploaded or text_input.strip():
            if uploaded:
                pdf_path = DATA_RAW / uploaded.name
                with open(pdf_path, "wb") as f:
                    f.write(uploaded.getbuffer())

                text = extract_text_from_pdf(str(pdf_path))

                if len(text) < 20:
                    st.warning("Scanned PDF detected → applying OCR…")
                    text = extract_text_with_ocr(str(pdf_path))
            else:
                text = text_input

            if len(text) < 20:
                st.error("Could not extract text")
            else:
                st.success("Document processed ✅")

                doc_type = detect_contract_type(text)
                clauses = detect_clauses_with_excerpts(text)
                risk, risk_comment = assess_risk(clauses)
                summary = summarize_text(text, 4)

                save_history(user, doc_type, risk, uploaded.name if uploaded else "Manual Text")

                # ✅ Summary
                st.subheader("🧠 Summary")
                st.success(summary)

                # ✅ CLAUSES UI (FOUND + MISSING)
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
                .found { color: green; }
                .missing { color: red; }
                </style>
                """, unsafe_allow_html=True)

                for clause, info in clauses.items():
                    icon = "✅" if info["found"] else "❌"
                    status = "found" if info["found"] else "missing"
                    excerpt = info["excerpt"][:200] + "..." if info["excerpt"] else ""

                    st.markdown(
                        f"""
                        <div class="clause-box">
                            <b>{clause}</b>
                            <span class="{status}" style="float:right">{icon} {status.title()}</span>
                            <br><small>{excerpt}</small>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # ✅ Extracted Text
                st.subheader("📜 Extracted Text")
                st.text_area("Text", text[:4000] + "...", height=250)

    # COMPARE DOCUMENTS
    elif choice == "🔍 Compare Documents":
        col1, col2 = st.columns(2)
        f1 = col1.file_uploader("First Document", type=["pdf"])
        f2 = col2.file_uploader("Second Document", type=["pdf"])

        if f1 and f2:
            p1 = DATA_RAW / f1.name
            p2 = DATA_RAW / f2.name
            with open(p1, "wb") as f:
                f.write(f1.getbuffer())
            with open(p2, "wb") as f:
                f.write(f2.getbuffer())

            t1 = extract_text_from_pdf(str(p1))
            t2 = extract_text_from_pdf(str(p2))

            sim = compare_versions(t1, t2)
            st.metric("Similarity", f"{sim}%")

    # REPORTS
    elif choice == "📊 Reports":
        st.subheader("History")
        history = json.loads(HISTORY_FILE.read_text()).get(user, [])
        for item in history:
            st.write(f"📄 {item['file']} → {item['type']} | Risk: {item['risk']}")

    # RISK ANALYSIS
    elif choice == "⚠ Risk Analysis":
        history = json.loads(HISTORY_FILE.read_text()).get(user, [])
        low = len([h for h in history if h["risk"] == "Low"])
        med = len([h for h in history if h["risk"] == "Medium"])
        high = len([h for h in history if h["risk"] == "High"])

        st.write(f"🟢 Low : {low}")
        st.write(f"🟡 Medium : {med}")
        st.write(f"🔴 High : {high}")


# ------------------ APP ENTRY ------------------
def main():
    st.set_page_config(page_title="AI Legal Analyzer", layout="wide")

    if "user" not in st.session_state:
        login_page()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()
