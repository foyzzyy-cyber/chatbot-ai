import streamlit as st
import streamlit.components.v1 as components
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
import re

# ===== KONFIGURASI HALAMAN =====
st.set_page_config(
    page_title="Rval AI - Asisten Cerdas",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
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
foto_profil_b64 = get_image_base64("foto_profil.png")

# ===== CSS MODERN =====
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    
    .stApp {{ background: radial-gradient(circle at top left, #1A1B3A 0%, #06080E 100%); }}
    
    [data-testid="stSidebar"] {{ 
        background-color: #0B0F19 !important; 
        border-right: 1px solid #1F2937;
        display: block !important;
    }}
    [data-testid="collapsedControl"] {{ display: none !important; }}

    [data-testid="stChatInput"] {{
        position: fixed !important;
        bottom: 0px !important;
        left: 0px !important;
        width: 100% !important;
        background: #06080E !important;
        padding: 15px 20px !important;
        z-index: 9999 !important;
        border-top: 1px solid #1F2937;
    }}
    .stChatInput {{
        padding-left: 320px !important; 
        padding-right: 400px !important;
    }}

    .chat-row {{ display: flex; width: 100%; margin-bottom: 25px; align-items: flex-start; }}
    .chat-row.user {{ justify-content: flex-end; }}
    .chat-row.user .bubble {{
        background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%);
        color: white; padding: 14px 20px; border-radius: 20px 20px 5px 20px;
        max-width: 75%; font-size: 15px; line-height: 1.6; width: fit-content; 
        box-shadow: 0 0 15px rgba(37, 99, 235, 0.5);
        border: 1px solid rgba(255,255,255,0.1);
    }}
    .chat-row.user .avatar {{ margin-left: 12px; width: 40px; height: 40px; border-radius: 50%; background-size: cover; flex-shrink: 0; border: 2px solid #2563EB; box-shadow: 0 0 10px rgba(37, 99, 235, 0.5); }}

    .chat-row.ai {{ justify-content: flex-start; }}
    .chat-row.ai .bubble {{
        background: rgba(17, 24, 39, 0.8); backdrop-filter: blur(12px); color: #E2E8F0;
        padding: 14px 20px; border-radius: 20px 20px 20px 5px; max-width: 80%; font-size: 15px; line-height: 1.6; 
        border: 1px solid rgba(59, 130, 246, 0.3);
        box-shadow: 0 0 10px rgba(0,0,0,0.5);
    }}
    .chat-row.ai .avatar {{ margin-right: 12px; width: 40px; height: 40px; border-radius: 50%; background-color: #1E293B; background-size: cover; flex-shrink: 0; border: 2px solid #3B82F6; box-shadow: 0 0 10px rgba(59, 130, 246, 0.6); }}

    .ai-profile {{ text-align: center; padding: 20px 0; background: linear-gradient(180deg, rgba(37,99,235,0.15) 0%, rgba(6,8,14,0) 100%); border-radius: 20px; margin-bottom: 20px; border: 1px solid rgba(37,99,235,0.2); }}
    .ai-avatar-big {{ width: 100px; height: 100px; background: #0B0F19; border-radius: 50%; margin: 0 auto 15px auto; display: flex; align-items: center; justify-content: center; font-size: 50px; border: 2px solid #2563EB; box-shadow: 0 0 30px rgba(37,99,235,0.6); }}
    
    .capability-item {{ display: flex; align-items: center; padding: 12px; border-radius: 12px; margin-bottom: 8px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); transition: all 0.3s ease; }}
    .capability-item:hover {{ background: rgba(37,99,235,0.1); border-color: rgba(37,99,235,0.3); }}
</style>
""", unsafe_allow_html=True)

# ===== SETUP API & LOGIN =====
client = Groq(api_key=st.secrets["GROQ_API_KEY"])   

# Cek apakah user login (lewat Google atau Tamu)
is_guest = st.session_state.get("guest_mode", False)
is_logged_in = st.user.is_logged_in or is_guest

if not is_logged_in:
    # === HALAMAN LOGIN MODERN (HTML/CSS MURNI) ===
    google_svg = '<svg width="20" height="20" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>'
    
    html_login = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        body {{
            margin: 0;
            padding: 0;
            height: 100vh;
            background: radial-gradient(circle at 10% 20%, #0d1b2a 0%, #06080E 100%);
            font-family: 'Inter', sans-serif;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }}
        .container {{
            display: flex;
            width: 90%;
            max-width: 1100px;
            justify-content: space-between;
            align-items: center;
            position: relative;
            z-index: 10;
        }}
        .left-panel {{
            flex: 1;
            padding-right: 50px;
            position: relative;
            z-index: 2;
        }}
        .logo {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 24px;
            font-weight: 800;
            margin-bottom: 40px;
        }}
        .logo-icon {{
            color: #3B82F6;
            font-size: 32px;
        }}
        h1 {{
            font-size: 48px;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 20px;
        }}
        .gradient-text {{
            background: linear-gradient(135deg, #60A5FA 0%, #A855F7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        p.subtitle {{
            color: #9CA3AF;
            font-size: 18px;
            margin-bottom: 40px;
            max-width: 400px;
        }}
        .features {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .feature-item {{
            display: flex;
            align-items: center;
            gap: 15px;
            font-size: 16px;
            font-weight: 500;
        }}
        .feature-icon {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: rgba(59, 130, 246, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #3B82F6;
        }}
        .right-panel {{
            flex: 1;
            display: flex;
            justify-content: flex-end;
            position: relative;
            z-index: 2;
        }}
        .login-card {{
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(30px);
            border-radius: 30px;
            padding: 50px;
            width: 100%;
            max-width: 450px;
            border: 1px solid rgba(59, 130, 246, 0.4);
            box-shadow: 0 0 50px rgba(37, 99, 235, 0.2), inset 0 0 20px rgba(37, 99, 235, 0.1);
            text-align: center;
            position: relative;
        }}
        .login-card::before {{
            content: "";
            position: absolute;
            top: -2px; left: -2px; right: -2px; bottom: -2px;
            background: linear-gradient(45deg, #3B82F6, #8B5CF6, #3B82F6);
            border-radius: 32px;
            z-index: -1;
            opacity: 0.5;
            filter: blur(15px);
        }}
        .card-icon {{
            width: 60px;
            height: 60px;
            background: rgba(59, 130, 246, 0.2);
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px auto;
            font-size: 30px;
            color: #3B82F6;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }}
        .login-card h2 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .login-card p {{
            color: #9CA3AF;
            font-size: 14px;
            margin-bottom: 30px;
        }}
        .btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            padding: 15px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            margin-bottom: 20px;
        }}
        .btn-google {{
            background: white;
            color: #000;
            border: none;
        }}
        .btn-google:hover {{
            background: #E5E7EB;
            transform: translateY(-2px);
        }}
        .btn-guest {{
            background: transparent;
            color: #3B82F6;
            border: 1px solid #3B82F6;
        }}
        .btn-guest:hover {{
            background: rgba(59, 130, 246, 0.1);
            transform: translateY(-2px);
        }}
        .divider {{
            display: flex;
            align-items: center;
            text-align: center;
            color: #4B5563;
            margin: 20px 0;
        }}
        .divider::before, .divider::after {{
            content: '';
            flex: 1;
            border-bottom: 1px solid #1F2937;
        }}
        .divider:not(:empty)::before {{ margin-right: 15px; }}
        .divider:not(:empty)::after {{ margin-left: 15px; }}
        .footer-text {{
            font-size: 12px;
            color: #6B7280;
            margin-top: 20px;
        }}
        .footer-text a {{ color: #3B82F6; text-decoration: none; }}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="left-panel">
                <div class="logo">
                    <span class="logo-icon">✨</span> Rval AI
                </div>
                <h1>Temukan cara baru<br>untuk <span class="gradient-text">berpikir.</span></h1>
                <p class="subtitle">Asisten AI cerdas untuk ide, belajar, dan produktivitas.</p>
                
                <div class="features">
                    <div class="feature-item">
                        <div class="feature-icon">⚡</div> Jawaban lebih cepat
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">💡</div> Ide tanpa batas
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">👤</div> Percakapan yang personal
                    </div>
                </div>
            </div>
            
            <div class="right-panel">
                <div class="login-card">
                    <div class="card-icon">🤖</div>
                    <h2>Selamat datang kembali 👋</h2>
                    <p>Masuk untuk melanjutkan percakapanmu</p>
                    
                    <a href="?login_guest=true" target="_self" class="btn btn-google">
                        {google_svg} 
                        Lanjutkan dengan Google
                    </a>
                    
                    <div class="divider">atau</div>
                    
                    <a href="?login_guest=true" target="_self" class="btn btn-guest">
                        <span>👤</span> Masuk sebagai tamu
                    </a>
                    
                    <div class="footer-text">
                        Dengan melanjutkan, kamu menyetujui<br>
                        <a href="#">Ketentuan Layanan</a> dan <a href="#">Kebijakan Privasi</a>.
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    components.html(html_login, height=700)
    
    # Tombol Streamlit (disembunyiin di bawah, dipicu lewat URL param)
    if "login_guest" in st.query_params:
        st.session_state.guest_mode = True
        st.query_params.clear() # Bersihin URL
        st.rerun()
    if "login_google" in st.query_params:
        st.login()
        st.query_params.clear()
        
    st.stop()

# Setup User Info
if is_guest:
    user_email = "tamu@guest.com" 
    display_name = "Tamu"
    avatar_to_use = "" 
else:
    user_email = st.user.email
    display_name = user_email.split("@")[0]
    avatar_to_use = user_avatar_b64

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

# ===== ATURAN PERSONA =====
PERSONAS = {
    "Asisten Ramah": "Kamu adalah Rval AI, asisten AI yang ramah. Jika menjelaskan matematika, SELALU gunakan format LaTeX dengan tanda $...$ untuk rumus inline, dan $$...$$ untuk rumus blok.",
    "Guru Matematika": "Kamu adalah Rval AI, guru matematika yang sabar. WAJIB pakai format LaTeX ($...$ atau $$...$$) untuk setiap rumus matematika.",
    "Koki Profesional": "Kamu adalah Rval AI, koki profesional.",
    "Programmer Expert": "Kamu adalah Rval AI, senior programmer."
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

# ===== FUNGSI RENDER PESAN =====
def render_pesan(teks, is_user=False):
    teks = teks.replace("\\[", "$").replace("\\]", "$").replace("\\(", "$").replace("\\)", "$")
    teks_html = markdown.markdown(teks, extensions=['markdown.extensions.extra', 'markdown.extensions.nl2br', 'markdown_katex'])
    teks_html = re.sub(r'(https?://\S+)', r'<a href="\1" target="_blank" style="color:#3B82F6; text-decoration:underline;">\1</a>', teks_html)

    if is_user:
        st.markdown(f'<div class="chat-row user"><div class="bubble">{teks_html}</div><div class="avatar" style="background-image: url(data:image/png;base64,{avatar_to_use});"></div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-row ai"><div class="avatar" style="background-image: url(data:image/png;base64,{bot_avatar_b64});"></div><div class="bubble">{teks_html}</div></div>', unsafe_allow_html=True)

# ===== SIDEBAR KIRI =====
with st.sidebar:
    st.markdown("<h2 style='color:#3B82F6; display:flex; align-items:center; gap:10px; text-shadow: 0 0 10px rgba(59,130,246,0.5);'><span style='font-size:30px;'>✨</span> Rval AI</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6B7280; font-size:12px; margin-top:-15px;'>Asisten Cerdas Anda</p>", unsafe_allow_html=True)
    
    if avatar_to_use:
        st.markdown(f'<div style="display:flex; align-items:center; gap:10px; margin:20px 0; padding:10px; background:rgba(255,255,255,0.05); border-radius:12px;"><div style="width:40px; height:40px; border-radius:50%; background-image: url(data:image/png;base64,{avatar_to_use}); background-size:cover; border: 2px solid #3B82F6;"></div><div><b>{display_name}</b><br><span style="font-size:10px; color:#6B7280;">{"Tamu" if is_guest else "Premium"}</span></div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="display:flex; align-items:center; gap:10px; margin:20px 0; padding:10px; background:rgba(255,255,255,0.05); border-radius:12px;"><div style="width:40px; height:40px; border-radius:50%; background:#1E293B; border: 2px solid #3B82F6; display:flex; align-items:center; justify-content:center; font-size:20px;">👤</div><div><b>{display_name}</b><br><span style="font-size:10px; color:#6B7280;">{"Tamu" if is_guest else "Premium"}</span></div></div>', unsafe_allow_html=True)
    
    if "menu" not in st.session_state: st.session_state.menu = "chat"
    
    if st.button("➕ Chat Baru", use_container_width=True, type="primary"):
        bikin_chat_baru(); st.session_state.menu = "chat"; st.rerun()
        
    if st.button("👨‍💻 Tentang Pembuat", use_container_width=True, type="secondary"):
        st.session_state.menu = "about"; st.rerun()
        
    st.markdown("<div style='height:1px; background:#1F2937; margin:15px 0;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='color:#E5E7EB; font-weight:600; margin-bottom:10px;'>💬 Chat</p>", unsafe_allow_html=True)
    
    if st.session_state.menu == "chat":
        for chat_id, chat_data in st.session_state.conversations.items():
            is_active = (chat_id == st.session_state.current_id)
            label = f"{'🟢 ' if is_active else '▫️ '}{chat_data['title']}"
            if st.button(label, key=f"chat_{chat_id}", use_container_width=True):
                st.session_state.current_id = chat_id; st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        st.selectbox("Pilih Kepribadian:", list(PERSONAS.keys()), key="persona")
    
    if st.button("Logout", use_container_width=True): 
        if is_guest:
            st.session_state.guest_mode = False
            st.rerun()
        else:
            st.logout()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(37,99,235,0.15) 0%, rgba(11,15,25,0.9) 100%); padding: 15px; border-radius: 15px; border: 1px solid rgba(37,99,235,0.3); margin-top: 20px;">
        <p style="color:#3B82F6; font-weight:bold; font-size:14px; margin-bottom:5px;">✨ Upgrade to Pro</p>
        <p style="font-size:10px; color:#9CA3AF; margin-bottom:10px;">Dapatkan fitur lebih lengkap.</p>
        <div style="background:#2563EB; text-align:center; padding:8px; border-radius:8px; color:white; font-size:12px; font-weight:bold; box-shadow: 0 0 10px rgba(37,99,235,0.4);">Upgrade</div>
    </div>
    """, unsafe_allow_html=True)

# ===== KONTEN UTAMA =====
if st.session_state.menu == "chat":
    col_chat, col_right = st.columns([2.5, 1])
    
    with col_right:
        st.markdown("""
        <div class="ai-profile">
            <div class="ai-avatar-big">🤖</div>
            <h3 style="margin:0; color:white;">Rval AI</h3>
            <p style="color:#9CA3AF; font-size:12px;">Selalu siap membantu 24/7</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<p style='color:#6B7280; font-size:11px; font-weight:bold; text-transform:uppercase; margin-bottom:10px;'>📄 Upload Dokumen</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Pilih file PDF", type=["pdf"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            if st.button("Proses PDF", use_container_width=True, type="primary"):
                with st.spinner("Membaca PDF..."):
                    pdf_text = extract_text_from_pdf(uploaded_file)
                    chat_aktif = ambil_chat_aktif()
                    chat_aktif["messages"].append({"role": "system", "content": f"Gunakan informasi dari dokumen berikut:\n\n{pdf_text[:10000]}"})
                    simpan_ke_file()
                    st.success("PDF berhasil diproses!")
                    st.rerun()

        st.markdown("<div style='height:1px; background:#1F2937; margin:15px 0;'></div>", unsafe_allow_html=True)
        st.markdown("<p style='color:#6B7280; font-size:11px; font-weight:bold; text-transform:uppercase; margin-bottom:10px;'>Kemampuan</p>", unsafe_allow_html=True)
        
        fitur = [("💬", "Tanya Jawab", "Dapatkan jawaban cepat"), ("📄", "Rangkuman", "Ringkas informasi panjang"), ("💡", "Kreativitas", "Ide, tulisan, dan konsep"), ("💻", "Pemrograman", "Bantuan coding dan debugging"), ("📚", "Belajar", "Jelaskan topik apa saja")]
        for icon, title, desc in fitur:
            st.markdown(f'<div class="capability-item"><div style="font-size:20px; margin-right:10px; background:rgba(37,99,235,0.2); padding:8px; border-radius:10px; color:#3B82F6;">{icon}</div><div><p style="margin:0; font-weight:bold; font-size:13px; color:white;">{title}</p><p style="margin:0; font-size:10px; color:#9CA3AF;">{desc}</p></div></div>', unsafe_allow_html=True)

    with col_chat:
        st.markdown(f'<div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #1F2937; margin-bottom:20px;"><div><h2 style="margin:0; color:white;">Chat dengan Rval AI</h2><p style="margin:0; font-size:12px; color:#9CA3AF;">Tanya apa saja!</p></div><div style="display:flex; align-items:center; gap:8px; background:rgba(34,197,94,0.1); color:#22C55E; padding:5px 15px; border-radius:20px; font-size:12px; font-weight:bold; border:1px solid rgba(34,197,94,0.2); box-shadow: 0 0 10px rgba(34,197,94,0.2);"><div style="width:8px; height:8px; border-radius:50%; background:#22C55E;"></div> Online</div></div>', unsafe_allow_html=True)

        chat = ambil_chat_aktif()
        if chat["messages"][0]["role"] == "system": chat["messages"][0]["content"] = get_system_prompt()

        for p in chat["messages"]:
            if p["role"] == "system": continue
            render_pesan(p["content"], is_user=(p["role"] == "user"))

        user = st.chat_input("Ketik pesan Anda di sini...")

        if user:
            if len(chat["messages"]) == 1: chat["title"] = user[:30] + ("..." if len(user) > 30 else "")
            chat["messages"].append({"role": "user", "content": user})
            render_pesan(user, is_user=True)

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

elif st.session_state.menu == "about":
    if foto_profil_b64:
        foto_html = f'<div style="width: 150px; height: 150px; border-radius: 50%; margin: 0 auto 20px auto; background-image: url(data:image/png;base64,{foto_profil_b64}); background-size: cover; background-position: center; border: 4px solid #2563EB; box-shadow: 0 0 40px rgba(37,99,235,0.6);"></div>'
    else:
        foto_html = '<div style="width: 150px; height: 150px; background: #1E293B; border-radius: 50%; margin: 0 auto 20px auto; display: flex; align-items: center; justify-content: center; font-size: 80px; border: 4px solid #2563EB; box-shadow: 0 0 40px rgba(37,99,235,0.6);">🧑‍💻</div>'

    html_content = f"""
    <div style="max-width: 800px; margin: 0 auto; padding-top: 20px;">
        <div style="background: linear-gradient(135deg, rgba(37,99,235,0.15) 0%, rgba(11,15,25,0.9) 100%); padding: 40px; border-radius: 20px; border: 1px solid rgba(37,99,235,0.3); text-align: center;">
            
            {foto_html}
            
            <h1 style="color: white; margin-bottom: 5px; font-size: 32px;">Revaldi Syahmaliah</h1>
            <p style="color: #3B82F6; font-size: 18px; font-weight: bold; margin-bottom: 30px;">Full-stack Developer & AI Enthusiast</p>
            
            <p style="color: #9CA3AF; font-size: 16px; line-height: 1.8; margin-bottom: 40px; text-align: justify;">
                Halo! Saya adalah seorang pengembang yang bersemangat dalam membangun aplikasi web modern dan mengintegrasikannya dengan Kecerdasan Buatan (AI). 
                Proyek ini dibuat sebagai portofolio untuk menunjukkan kemampuan saya dalam menggabungkan Python (Streamlit), JavaScript (React), dan API AI (Groq) menjadi satu kesatuan aplikasi yang fungsional dan estetik.
            </p>
            
            <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
                <a href="https://github.com/foyzzyy-cyber" target="_blank" style="text-decoration: none; background: #1F2937; padding: 12px 24px; border-radius: 10px; color: white; font-weight: bold; display: flex; align-items: center; gap: 8px; transition: 0.3s;">
                    <span style="font-size: 20px;">🐙</span> GitHub Saya
                </a>
                <a href="https://www.instagram.com/rqpnsyq" target="_blank" style="text-decoration: none; background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); padding: 12px 24px; border-radius: 10px; color: white; font-weight: bold; display: flex; align-items: center; gap: 8px; transition: 0.3s;">
                    <span style="font-size: 20px;">📸</span> Instagram Saya
                </a>
            </div>
        </div>
    </div>
    """
    components.html(html_content, height=600, scrolling=True)
