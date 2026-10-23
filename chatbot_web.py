import streamlit as st
from groq import Groq
import uuid
import json
from pypdf import PdfReader
import os
import requests
from bs4 import BeautifulSoup
import markdown
import sqlite3
import base64

# ===== KONFIGURASI HALAMAN =====
st.set_page_config(
    page_title="AI Portofolio",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed" # <--- SIDEBAR BAWAAN DIMATIIN
)

# ===== FUNGSI AVATAR =====
def get_image_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""

user_avatar_b64 = get_image_base64("user_avatar.png")
bot_avatar_b64 = get_image_base64("bot_avatar.png")

# ===== CSS MODERN =====
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    
    .stApp {{ background: radial-gradient(circle at top left, #1A1B3A 0%, #0B0F19 100%); }}
    
    /* Sembunyiin sidebar bawaan Streamlit */
    [data-testid="stSidebar"] {{ display: none !important; }}
    [data-testid="collapsedControl"] {{ display: none !important; }}

    /* Chat Bubble Custom */
    .chat-row {{ display: flex; width: 100%; margin-bottom: 25px; align-items: flex-start; }}
    .chat-row.user {{ justify-content: flex-end; }}
    .chat-row.user .bubble {{
        background: linear-gradient(135deg, #7C3AED 0%, #A855F7 100%);
        color: white; padding: 14px 20px; border-radius: 20px 20px 5px 20px;
        max-width: 75%; font-size: 15px; line-height: 1.6; width: fit-content; box-shadow: 0 8px 20px rgba(124, 58, 237, 0.3);
    }}
    .chat-row.user .avatar {{ margin-left: 12px; width: 40px; height: 40px; border-radius: 50%; background-size: cover; flex-shrink: 0; border: 2px solid #7C3AED; }}

    .chat-row.ai {{ justify-content: flex-start; }}
    .chat-row.ai .bubble {{
        background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); color: #E2E8F0;
        padding: 14px 20px; border-radius: 20px 20px 20px 5px; max-width: 80%; font-size: 15px; line-height: 1.6; border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .chat-row.ai .avatar {{ margin-right: 12px; width: 40px; height: 40px; border-radius: 50%; background-color: #7C3AED; background-size: cover; flex-shrink: 0; border: 2px solid #A855F7; box-shadow: 0 0 10px rgba(168, 85, 247, 0.4); }}

    /* Panel Kanan */
    .ai-profile {{ text-align: center; padding: 20px 0; background: linear-gradient(180deg, rgba(124,58,237,0.2) 0%, rgba(17,24,39,0) 100%); border-radius: 20px; margin-bottom: 20px; }}
    .ai-avatar-big {{ width: 80px; height: 80px; background: #1E293B; border-radius: 50%; margin: 0 auto 15px auto; display: flex; align-items: center; justify-content: center; font-size: 40px; border: 2px solid #7C3AED; box-shadow: 0 0 20px rgba(124,58,237,0.5); }}
    .capability-item {{ display: flex; align-items: center; padding: 10px; border-radius: 12px; margin-bottom: 8px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); }}
</style>
""", unsafe_allow_html=True)

# ===== SETUP API & LOGIN =====
client = Groq(api_key=st.secrets["GROQ_API_KEY"])   

if not st.user.is_logged_in:
    st.markdown('<div style="text-align:center; margin-top:20vh;"><h1>🤖 AI Portofolio</h1><p>Silakan login untuk mulai.</p></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button("Login with Google", type="primary", use_container_width=True):
            st.login()
    st.stop()

user_email = st.user.email
folder_user = f"data_{user_email.replace('@', '_').replace('.', '_')}"
os.makedirs(folder_user, exist_ok=True)

# ===== DATABASE =====
DB_PATH = os.path.join(folder_user, "chat_history.db")
def init_db():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, title TEXT, messages TEXT)''')
    conn.commit(); conn.close()

def simpan_ke_db(chat_id, title, messages):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    messages_json = json.dumps(messages, ensure_ascii=False)
    c.execute("INSERT OR REPLACE INTO conversations (id, title, messages) VALUES (?, ?, ?)", (chat_id, title, messages_json))
    conn.commit(); conn.close()

def muat_dari_db():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT id, title, messages FROM conversations")
    rows = c.fetchall(); conn.close()
    data = {}
    for row in rows:
        data[row[0]] = {"title": row[1], "messages": json.loads(row[2])}
    return data
init_db()

PERSONAS = {
    "Asisten Ramah": "Kamu adalah asisten AI yang ramah, santai, dan membantu.",
    "Guru Matematika": "Kamu adalah guru matematika yang sabar.",
    "Koki Profesional": "Kamu adalah koki profesional.",
    "Programmer Expert": "Kamu adalah senior programmer."
}
def get_system_prompt(): return PERSONAS[st.session_state.get("persona", "Asisten Ramah")]

def simpan_ke_file():
    for chat_id, chat_data in st.session_state.conversations.items(): simpan_ke_db(chat_id, chat_data["title"], chat_data["messages"])
def muat_dari_file(): return muat_dari_db()
def extract_text_from_pdf(file):
    reader = PdfReader(file); text = ""
    for page in reader.pages: text += page.extract_text() + "\n"
    return text
def ambil_teks_dari_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]): script.decompose()
        return soup.get_text(separator=' ', strip=True)[:15000]
    except Exception as e: return f"Error: Gagal mengambil teks. ({e})"

def bikin_chat_baru():
    new_id = str(uuid.uuid4())[:8]
    st.session_state.conversations[new_id] = {"title": "Chat Baru", "messages": [{"role": "system", "content": get_system_prompt()}]}
    st.session_state.current_id = new_id; simpan_ke_file()
def ambil_chat_aktif(): return st.session_state.conversations[st.session_state.current_id]

if "conversations" not in st.session_state: st.session_state.conversations = muat_dari_file() or {}
if "current_id" not in st.session_state:
    if st.session_state.conversations: st.session_state.current_id = list(st.session_state.conversations.keys())[0]
    else: bikin_chat_baru()

# ===== LAYOUT UTAMA (2 KOLOM: CHAT & PANEL KANAN) =====
col_chat, col_right = st.columns([2.5, 1])

# --- KOLOM KANAN (PANEL AI, MENU, & HISTORY) ---
with col_right:
    # 1. Profil AI
    st.markdown("""
    <div class="ai-profile">
        <div class="ai-avatar-big">🤖</div>
        <h3 style="margin:0; color:white;">AI Assistant</h3>
        <p style="color:#9CA3AF; font-size:12px;">Selalu siap membantu 24/7</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. User Info & Logout
    if user_avatar_b64:
        st.markdown(f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; background:rgba(255,255,255,0.05); padding:10px; border-radius:10px;"><div style="width:35px; height:35px; border-radius:50%; background-image: url(data:image/png;base64,{user_avatar_b64}); background-size:cover; border: 2px solid #A855F7;"></div><div><b style="font-size:13px;">{user_email.split("@")[0]}</b><br><span style="font-size:10px; color:#6B7280;">Premium</span></div></div>', unsafe_allow_html=True)
    if st.button("Logout", use_container_width=True): st.logout()
    
    st.markdown("<div style='height:1px; background:#1F2937; margin:10px 0;'></div>", unsafe_allow_html=True)
    
    # 3. Tombol Chat Baru
    if st.button("➕ Chat Baru", use_container_width=True, type="primary"):
        bikin_chat_baru(); st.rerun()
        
    # 4. Pilih Persona
    st.selectbox("Pilih Kepribadian:", list(PERSONAS.keys()), key="persona")
    
    st.markdown("<div style='height:1px; background:#1F2937; margin:10px 0;'></div>", unsafe_allow_html=True)
    
    # 5. History Chat
    st.markdown("<p style='color:#E5E7EB; font-weight:600; font-size:12px; margin-bottom:5px;'>History</p>", unsafe_allow_html=True)
    for chat_id, chat_data in st.session_state.conversations.items():
        is_active = (chat_id == st.session_state.current_id)
        label = f"{'🟢 ' if is_active else '▫️ '}{chat_data['title']}"
        if st.button(label, key=f"chat_{chat_id}", use_container_width=True):
            st.session_state.current_id = chat_id; st.rerun()
            
    # 6. Daftar Kemampuan (di paling bawah)
    st.markdown("<div style='height:1px; background:#1F2937; margin:15px 0;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6B7280; font-size:10px; font-weight:bold; text-transform:uppercase; margin-bottom:10px;'>Kemampuan</p>", unsafe_allow_html=True)
    fitur = [("💬", "Tanya Jawab"), ("📄", "Rangkuman"), ("💡", "Kreativitas"), ("💻", "Pemrograman"), ("📚", "Belajar")]
    for icon, title in fitur:
        st.markdown(f'<div class="capability-item" style="padding:8px;"><div style="font-size:16px; margin-right:8px;">{icon}</div><p style="margin:0; font-size:12px; color:white;">{title}</p></div>', unsafe_allow_html=True)

# --- KOLOM KIRI (CHAT) ---
with col_chat:
    # Header Chat
    st.markdown(f'<div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #1F2937; margin-bottom:20px;"><div><h2 style="margin:0; color:white;">Chat dengan AI</h2><p style="margin:0; font-size:12px; color:#9CA3AF;">Tanya apa saja!</p></div><div style="display:flex; align-items:center; gap:8px; background:rgba(34,197,94,0.1); color:#22C55E; padding:5px 15px; border-radius:20px; font-size:12px; font-weight:bold; border:1px solid rgba(34,197,94,0.2);"><div style="width:8px; height:8px; border-radius:50%; background:#22C55E;"></div> Online</div></div>', unsafe_allow_html=True)

    chat = ambil_chat_aktif()
    if chat["messages"][0]["role"] == "system": chat["messages"][0]["content"] = get_system_prompt()

    # Tampilkan Chat History
    for p in chat["messages"]:
        if p["role"] == "system": continue
        teks_html = markdown.markdown(p["content"])
        if p["role"] == "user":
            avatar_style = f'style="background-image: url(data:image/png;base64,{user_avatar_b64});"' if user_avatar_b64 else ''
            st.markdown(f'<div class="chat-row user"><div class="bubble">{teks_html}</div><div class="avatar" {avatar_style}></div></div>', unsafe_allow_html=True)
        else:
            avatar_style = f'style="background-image: url(data:image/png;base64,{bot_avatar_b64});"' if bot_avatar_b64 else ''
            st.markdown(f'<div class="chat-row ai"><div class="avatar" {avatar_style}></div><div class="bubble">{teks_html}</div></div>', unsafe_allow_html=True)

    # Input Chat
    user = st.chat_input("Ketik pesan Anda di sini...")

    if user:
        if len(chat["messages"]) == 1: chat["title"] = user[:30] + ("..." if len(user) > 30 else "")
        chat["messages"].append({"role": "user", "content": user})
        teks_html_user = markdown.markdown(user)
        avatar_style = f'style="background-image: url(data:image/png;base64,{user_avatar_b64});"' if user_avatar_b64 else ''
        st.markdown(f'<div class="chat-row user"><div class="bubble">{teks_html_user}</div><div class="avatar" {avatar_style}></div></div>', unsafe_allow_html=True)

        with st.spinner(""):
            try:
                stream = client.chat.completions.create(model="openai/gpt-oss-120b", messages=chat["messages"], stream=True)
                def generate_chunks():
                    for chunk in stream:
                        if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
                jawab = st.write_stream(generate_chunks())
                if jawab:
                    chat["messages"].append({"role": "assistant", "content": jawab})
                    simpan_ke_file(); st.rerun()
            except Exception as e: st.error(f"⚠️ Error: {e}")
