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
    page_title="AI Portofolio Revaldi",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ===== FUNGSI BUAT NGELOAD GAMBAR AVATAR =====
def get_image_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""

user_avatar_b64 = get_image_base64("user_avatar.png")
bot_avatar_b64 = get_image_base64("bot_avatar.png")

# ===== CSS CUSTOM SUPER KEREN =====
st.markdown(f"""
<style>
    /* 1. Sembunyiin header & footer bawaan Streamlit biar bersih */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* 2. Atur jarak konten utama */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 800px;
    }}

    /* 3. Font yang lebih modern */
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    /* 4. Container Chat */
    .chat-row {{
        display: flex;
        width: 100%;
        margin-bottom: 20px;
        align-items: flex-start;
    }}
    
    /* 5. Layout User (Kanan) */
    .chat-row.user {{
        justify-content: flex-end;
    }}
    .chat-row.user .bubble {{
        background-color: #2D2D2D; /* Warna abu gelap ala ChatGPT */
        color: white;
        padding: 12px 18px;
        border-radius: 12px;
        max-width: 80%;
        font-size: 15px;
        line-height: 1.6;
    }}
    .chat-row.user .avatar {{
        margin-left: 12px;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background-color: #444;
        background-size: cover;
        flex-shrink: 0;
    }}

    /* 6. Layout AI (Kiri) */
    .chat-row.ai {{
        justify-content: flex-start;
    }}
    .chat-row.ai .bubble {{
        background-color: transparent; /* AI tanpa background ala Claude */
        color: #E0E0E0;
        padding: 12px 18px 12px 0px;
        border-radius: 12px;
        max-width: 85%;
        font-size: 15px;
        line-height: 1.6;
    }}
    .chat-row.ai .avatar {{
        margin-right: 12px;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background-color: #A855F7; /* Warna ungu buat AI */
        background-size: cover;
        flex-shrink: 0;
    }}
    
    /* 7. Welcome Screen yang lebih classy */
    .welcome-container {{
        text-align: center;
        margin-top: 20vh;
    }}
    .welcome-container h1 {{
        color: #A855F7;
        font-size: 2.5em;
        font-weight: 700;
        margin-bottom: 10px;
    }}
    .welcome-container p {{
        color: #888;
        font-size: 16px;
    }}
</style>
""", unsafe_allow_html=True)


# ===== SETUP API & LOGIN =====
client = Groq(api_key=st.secrets["GROQ_API_KEY"])   

if not st.user.is_logged_in:
    st.markdown('<div class="welcome-container"><h1>🤖 AI Portofolio</h1><p>Silakan login untuk mulai.</p></div>', unsafe_allow_html=True)
    if st.button("Login with Google", type="primary", use_container_width=True):
        st.login()
    st.stop()

user_email = st.user.email
folder_user = f"data_{user_email.replace('@', '_').replace('.', '_')}"
os.makedirs(folder_user, exist_ok=True)

# ===== SETUP DATABASE SQLITE =====
DB_PATH = os.path.join(folder_user, "chat_history.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, title TEXT, messages TEXT)''')
    conn.commit()
    conn.close()

def simpan_ke_db(chat_id, title, messages):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    messages_json = json.dumps(messages, ensure_ascii=False)
    c.execute("INSERT OR REPLACE INTO conversations (id, title, messages) VALUES (?, ?, ?)", (chat_id, title, messages_json))
    conn.commit()
    conn.close()

def muat_dari_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, messages FROM conversations")
    rows = c.fetchall()
    conn.close()
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

def get_system_prompt():
    return PERSONAS[st.session_state.get("persona", "Asisten Ramah")]

# ===== FUNGSI SIMPAN & MUAT =====
def simpan_ke_file():
    for chat_id, chat_data in st.session_state.conversations.items():
        simpan_ke_db(chat_id, chat_data["title"], chat_data["messages"])

def muat_dari_file():
    return muat_dari_db()

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def ambil_teks_dari_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]): script.decompose()
        return soup.get_text(separator=' ', strip=True)[:15000]
    except Exception as e:
        return f"Error: Gagal mengambil teks dari URL. ({e})"

# ===== FUNGSI BANTU =====
def bikin_chat_baru():
    new_id = str(uuid.uuid4())[:8]
    st.session_state.conversations[new_id] = {
        "title": "Chat Baru",
        "messages": [{"role": "system", "content": get_system_prompt()}]
    }
    st.session_state.current_id = new_id
    simpan_ke_file()

def ambil_chat_aktif():
    return st.session_state.conversations[st.session_state.current_id]

# ===== INISIALISASI STATE =====
if "conversations" not in st.session_state:
    st.session_state.conversations = muat_dari_file() or {}

if "current_id" not in st.session_state:
    if st.session_state.conversations:
        st.session_state.current_id = list(st.session_state.conversations.keys())[0]
    else:
        bikin_chat_baru()

# ===== SIDEBAR =====
with st.sidebar:
    st.title("💬 Obrolan")
    
    if user_avatar_b64:
        st.markdown(f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:20px;"><div style="width:40px; height:40px; border-radius:50%; background-image: url(data:image/png;base64,{user_avatar_b64}); background-size:cover;"></div><div><b>{user_email.split("@")[0]}</b><br><span style="font-size:12px; color:gray;">{user_email}</span></div></div>', unsafe_allow_html=True)
    
    if st.button("Logout", use_container_width=True):
        st.logout()
    
    st.markdown("---")
    st.selectbox("Mode AI:", list(PERSONAS.keys()), key="persona")
    
    if st.button("➕ Obrolan Baru", use_container_width=True, type="primary"):
        bikin_chat_baru()
        st.rerun()
    
    st.markdown("---")
    
    for chat_id, chat_data in st.session_state.conversations.items():
        is_active = (chat_id == st.session_state.current_id)
        label = f"{'🟢 ' if is_active else '▫️ '}{chat_data['title']}"
        if st.button(label, key=f"chat_{chat_id}", use_container_width=True):
            st.session_state.current_id = chat_id
            st.rerun()
    
    if len(st.session_state.conversations) > 1:
        if st.button("🗑️ Hapus Obrolan", use_container_width=True):
            del st.session_state.conversations[st.session_state.current_id]
            st.session_state.current_id = list(st.session_state.conversations.keys())[0]
            simpan_ke_file()
            st.rerun()

    st.markdown("---")
    
    chat_aktif = ambil_chat_aktif()
    teks_chat = "".join([f"{msg['role'].upper()}: {msg['content']}\n\n" for msg in chat_aktif["messages"] if msg["role"] != "system"])
    st.download_button("📥 Download Obrolan", data=teks_chat, file_name=f"chat_{chat_aktif['title']}.txt", mime="text/plain", use_container_width=True)

    st.markdown("---")
    st.subheader("📄 Baca File")
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded_file and st.button("Proses PDF", use_container_width=True):
        with st.spinner("Membaca..."):
            pdf_text = extract_text_from_pdf(uploaded_file)
            chat_aktif["messages"].append({"role": "system", "content": f"Gunakan info dokumen ini:\n\n{pdf_text[:10000]}"})
            simpan_ke_file()
            st.success("Berhasil!")
            st.rerun()

    st.subheader("🌐 Baca Web")
    url_input = st.text_input("Tempel URL:", label_visibility="collapsed")
    if st.button("Proses Link", use_container_width=True):
        if url_input:
            with st.spinner("Membaca..."):
                teks_web = ambil_teks_dari_url(url_input)
                chat_aktif["messages"].append({"role": "system", "content": f"Gunakan info web ini:\n\n{teks_web}"})
                simpan_ke_file()
                st.success("Berhasil!")
                st.rerun()

# ===== AREA CHAT =====
chat = ambil_chat_aktif()

if chat["messages"][0]["role"] == "system":
    chat["messages"][0]["content"] = get_system_prompt()

if len(chat["messages"]) == 1:
    st.markdown("""
    <div class="welcome-container">
        <h1>Ada yang bisa dibantu?</h1>
        <p>Silakan ketik pertanyaan, upload PDF, atau masukin link artikel.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for p in chat["messages"]:
        if p["role"] == "system": continue
        teks_html = markdown.markdown(p["content"])
        
        if p["role"] == "user":
            avatar_style = f'style="background-image: url(data:image/png;base64,{user_avatar_b64});"' if user_avatar_b64 else ''
            avatar_content = '' if user_avatar_b64 else '🧑'
            st.markdown(f'''
            <div class="chat-row user">
                <div class="bubble">{teks_html}</div>
                <div class="avatar" {avatar_style}>{avatar_content}</div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            avatar_style = f'style="background-image: url(data:image/png;base64,{bot_avatar_b64});"' if bot_avatar_b64 else ''
            avatar_content = '' if bot_avatar_b64 else '🤖'
            st.markdown(f'''
            <div class="chat-row ai">
                <div class="avatar" {avatar_style}>{avatar_content}</div>
                <div class="bubble">{teks_html}</div>
            </div>
            ''', unsafe_allow_html=True)

# Input user
user = st.chat_input("Ketik pesan di sini...")

if user:
    if len(chat["messages"]) == 1:
        chat["title"] = user[:30] + ("..." if len(user) > 30 else "")
    
    chat["messages"].append({"role": "user", "content": user})
    teks_html_user = markdown.markdown(user)
    avatar_style = f'style="background-image: url(data:image/png;base64,{user_avatar_b64});"' if user_avatar_b64 else ''
    avatar_content = '' if user_avatar_b64 else '🧑'
    
    st.markdown(f'''
    <div class="chat-row user">
        <div class="bubble">{teks_html_user}</div>
        <div class="avatar" {avatar_style}>{avatar_content}</div>
    </div>
    ''', unsafe_allow_html=True)

    with st.spinner(""):
        try:
            stream = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=chat["messages"],
                stream=True 
            )
            
            def generate_chunks():
                for chunk in stream:
                    if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            
            jawab = st.write_stream(generate_chunks())
            
            if jawab:
                chat["messages"].append({"role": "assistant", "content": jawab})
                simpan_ke_file()
                st.rerun()
        except Exception as e:
            st.error(f"⚠️ Error: {e}")
