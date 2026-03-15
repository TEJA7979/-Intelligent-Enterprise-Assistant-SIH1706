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