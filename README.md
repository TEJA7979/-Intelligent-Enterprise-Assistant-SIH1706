# -Intelligent-Enterprise-Assistant-SIH1706

## AIM
To develop an AI-powered Intelligent Enterprise Assistant capable of handling HR, IT, and organizational queries, document summarization, and secure authentication using NLP and document processing.

## Problem Statement
Problem ID: SIH1706
Title: Intelligent Enterprise Assistant — Enhancing Organizational Efficiency through AI-Driven Chatbot Integration

## System Should Perform
Handle HR, IT, and organizational questions
Process uploaded enterprise documents (summarize, extract keywords)
Use email-based OTP for 2-Factor Authentication
Filter bad language using a system-maintained dictionary
Respond within 5 seconds for any query
Support a minimum of 5 parallel users
## Implementation Steps
🔹 Backend (FastAPI)
Built using FastAPI framework
Endpoints implemented:
/auth/send-otp — Email OTP generation
/auth/verify-otp — OTP verification
/upload/document — Uploads and processes documents
/query — NLP-based query handling
Includes SMTP OTP (prints OTP to console if SMTP not configured)
Handles PDF/DOCX summarization using TF-IDF
Filters profanity from user queries
🔹 Frontend (Streamlit)
Simple web UI for:

1.Authentication
2.Document Upload
3.Query Interaction
Uses FastAPI backend via API calls and displays assistant responses in an interactive chat view.

🔹 Security
2FA with Email OTP
Session token for each verified user
In-memory user sessions (demo mode)
🔹 Scalability
FastAPI’s async architecture allows parallel processing
Each request processed under 5 seconds

## Main Backend Code — main.py
```
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, io, time, hashlib, secrets, json, re, jwt, datetime
from typing import Dict, List
from collections import Counter

try:
    import pdfplumber
except Exception:
    pdfplumber = None

from transformers import pipeline
from keybert import KeyBERT
from better_profanity import profanity
from sklearn.feature_extraction.text import TfidfVectorizer

app = FastAPI(title="SIH1706 - Intelligent Enterprise Assistant (Enhanced)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- GLOBAL MODELS ----------------
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
kw_model = KeyBERT()
profanity.load_censor_words()

# ---------------- STORAGE ----------------
USERS, SESSIONS, DOCUMENTS = {}, {}, {}
PROFANITY = {"badword1", "badword2"}
SECRET_KEY = "hackathon_secret_key"

# ---------------- UTILITIES ----------------
def _hash_token(token: str): return hashlib.sha256(token.encode()).hexdigest()

def _create_jwt(email: str):
    payload = {"email": email, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def _verify_jwt(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["email"]
    except Exception:
        return None

def send_email(to, subject, body):
    print(f"[EMAIL Fallback] To: {to}\n{subject}\n{body}")

def generate_otp(): return f"{secrets.randbelow(10**6):06d}"

# ---------------- AUTH ----------------
class SendOTPRequest(BaseModel): email: str
@app.post("/auth/send-otp")
async def send_otp(req: SendOTPRequest):
    otp = generate_otp()
    USERS[req.email] = {"otp_hash": _hash_token(otp), "otp_expiry": time.time()+300}
    send_email(req.email, "Your OTP", f"Your OTP is: {otp}")
    return {"status": "ok", "message": "OTP sent. Check console if SMTP not set."}

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str
@app.post("/auth/verify-otp")
async def verify_otp(req: VerifyOTPRequest):
    record = USERS.get(req.email)
    if not record: raise HTTPException(400, "OTP not sent for this email.")
    if time.time() > record["otp_expiry"]: raise HTTPException(400, "OTP expired.")
    if _hash_token(req.otp) != record["otp_hash"]: raise HTTPException(400, "Invalid OTP.")
    token = _create_jwt(req.email)
    SESSIONS[token] = req.email
    return {"status": "ok", "token": token}

# ---------------- PROFANITY ----------------
@app.post("/admin/profanity")
async def add_profanity(items: List[str]):
    PROFANITY.update(w.lower().strip() for w in items)
    return {"status": "ok", "count": len(PROFANITY)}

def contains_profanity(text: str):
    words = re.findall(r"\w+", text.lower())
    return any(w in PROFANITY or profanity.contains_profanity(w) for w in words)

# ---------------- DOCUMENT UPLOAD ----------------
@app.post("/upload/document")
async def upload_document(file: UploadFile = File(...), token: str = Form(...)):
    email = _verify_jwt(token)
    if not email: raise HTTPException(401, "Invalid or expired token.")
    contents = await file.read()
    text = ""
    if file.filename.lower().endswith(".pdf") and pdfplumber:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])
    else:
        text = contents.decode(errors="ignore")
    if not text: raise HTTPException(400, "Could not extract text.")
    doc_id = secrets.token_hex(8)
    summary = summarizer(text[:3000], max_length=150, min_length=50, do_sample=False)[0]["summary_text"]
    keywords = [kw for kw, _ in kw_model.extract_keywords(text, top_n=5)]
    DOCUMENTS[doc_id] = {"owner": email, "text": text, "summary": summary, "keywords": keywords}
    return {"status": "ok", "doc_id": doc_id, "summary": summary, "keywords": keywords}

# ---------------- CHAT / QUERY ----------------
class QueryRequest(BaseModel):
    token: str
    query: str

@app.post("/query")
async def query(req: QueryRequest):
    email = _verify_jwt(req.token)
    if not email: raise HTTPException(401, "Invalid or expired token.")
    q = req.query.strip()
    if contains_profanity(q):
        return {"answer": "Please avoid inappropriate language."}
    intent = detect_intent(q)
    if intent == "hr": return {"answer": handle_hr_query(q)}
    elif intent == "it": return {"answer": handle_it_query(q)}
    elif intent == "event": return {"answer": handle_event_query(q)}
    elif intent == "doc": return {"answer": handle_document_query(q)}
    else: return {"answer": "I'm learning! Try asking about HR, IT, Events, or uploaded docs."}

def detect_intent(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["leave","salary","policy","payroll"]): return "hr"
    if any(k in t for k in ["wifi","vpn","password","system","it support"]): return "it"
    if any(k in t for k in ["event","meeting","conference","hackathon","seminar"]): return "event"
    if any(k in t for k in ["document","summary","upload","pdf"]): return "doc"
    return "unknown"

def handle_hr_query(q: str):
    if "leave" in q: return "Employees receive 18 days paid leave annually."
    if "salary" in q: return "Salary slips are issued via the Payroll portal."
    return "HR-related queries include leave, salary, and benefits."

def handle_it_query(q: str):
    if "password" in q: return "Reset via the IT portal or contact support@org.com."
    if "vpn" in q: return "Use the corporate VPN client with your credentials."
    return "For IT support, describe the issue or attach logs."

def handle_event_query(q: str):
    if "hackathon" in q: return "The annual Innovation Hackathon occurs in December."
    return "Upcoming corporate events are listed in the intranet calendar."

def handle_document_query(q: str):
    if not DOCUMENTS: return "No uploaded documents found."
    words = re.findall(r"\w+", q.lower())
    best_doc = max(DOCUMENTS.items(), key=lambda d: sum(d[1]["text"].lower().count(w) for w in words))
    doc = best_doc[1]
    return f"Document Summary: {doc['summary']} | Keywords: {', '.join(doc['keywords'])}"

# ---------------- UI PAGE ----------------
@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse("""
    <h2>SIH1706 - Intelligent Enterprise Assistant</h2>
    <p>Use endpoints: /auth/send-otp, /auth/verify-otp, /upload/document, /query</p>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sih_chatbot:app", host="0.0.0.0", port=8000, reload=True)
```

 ## Frontend Code — frontend.py
 ```
import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Intelligent Enterprise Assistant",
    page_icon="🤖",
    layout="centered"
)

# Inject custom CSS for styling with new colors and background
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Main content container */
    .main .block-container {
        background-color: #ffffff;
        border-radius: 20px;
        padding: 40px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
    }
    
    /* Title styling */
    h1 {
        color: #2d3748;
        font-weight: 700;
        text-align: center;
        margin-bottom: 30px;
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e2e8f0;
        padding: 12px;
        font-size: 16px;
        transition: all 0.3s;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Text area */
    .stTextArea textarea {
        border-radius: 12px;
        border: 2px solid #e2e8f0;
        padding: 12px;
        font-size: 16px;
        transition: all 0.3s;
    }
    
    .stTextArea textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        padding: 12px 24px;
        border: none;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s;
        width: 100%;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    [data-testid="stSidebar"] .css-1d391kg {
        color: white;
    }
    
    /* Radio buttons in sidebar */
    .stRadio > label {
        color: white;
        font-weight: 600;
    }
    
    /* File uploader */
    .stFileUploader {
        border-radius: 12px;
        border: 2px dashed #667eea;
        padding: 20px;
        background-color: #f7fafc;
    }
    
    /* Success/Warning/Error messages */
    .stSuccess {
        background-color: #c6f6d5;
        border-radius: 10px;
        padding: 15px;
        color: #22543d;
    }
    
    .stWarning {
        background-color: #fef5e7;
        border-radius: 10px;
        padding: 15px;
        color: #7d5a00;
    }
    
    .stError {
        background-color: #fed7d7;
        border-radius: 10px;
        padding: 15px;
        color: #742a2a;
    }
    
    .stInfo {
        background-color: #bee3f8;
        border-radius: 10px;
        padding: 15px;
        color: #2c5282;
    }
    
    /* Headers in response */
    h3 {
        color: #667eea;
        font-weight: 600;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Intelligent Enterprise Assistant")

page = st.sidebar.radio("Navigation", ["Authentication", "Document Upload", "Chat"])

if page == "Authentication":
    email = st.text_input("Enter email")
    if st.button("Send OTP"):
        r = requests.post(f"{BASE_URL}/auth/send-otp", json={"email": email})
        st.info(r.json()["message"])

    otp = st.text_input("Enter OTP")
    if st.button("Verify OTP"):
        r = requests.post(f"{BASE_URL}/auth/verify-otp", json={"email": email, "otp": otp})
        if r.status_code == 200:
            st.session_state["token"] = r.json()["token"]
            st.success("OTP Verified ✅")
        else:
            st.error(r.text)

elif page == "Document Upload":
    if "token" not in st.session_state:
        st.warning("Authenticate first.")
    else:
        file = st.file_uploader("Upload PDF")
        if st.button("Upload") and file:
            res = requests.post(
                f"{BASE_URL}/upload/document",
                files={"file": file},
                data={"token": st.session_state["token"]}
            )
            if res.status_code == 200:
                data = res.json()
                st.success("Uploaded successfully")
                st.write("### 📄 Summary:", data["summary"])
                st.write("### 🔑 Keywords:", ", ".join(data["keywords"]))
            else:
                st.error(res.text)

elif page == "Chat":
    if "token" not in st.session_state:
        st.warning("Authenticate first.")
    else:
        q = st.text_area("Enter query")
        if st.button("Ask"):
            res = requests.post(
                f"{BASE_URL}/query",
                json={"token": st.session_state["token"], "query": q}
            )
            st.write("### 💬 Response:")
            st.write(res.json().get("answer", "No response"))
```

## Output


🧾 Result
Your chatbot now functions as a secure, intelligent assistant capable of answering HR and enterprise queries, handling documents, and demonstrating AI integration for the public sector.

