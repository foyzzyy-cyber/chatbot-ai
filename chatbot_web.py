import streamlit as st
from groq import Groq
import uuid
import json
from pypdf import PdfReader
import os
import requests
from bs4 import BeautifulSoup
import sqlite3
import base64
import re
import markdown

# ===== KONFIGURASI HALAMAN =====
st.set_page_config(
    page_title="AI Portofolio",
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

# ===== CSS MODERN =====
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    
    .stApp {{ background: #06080E; }}
    
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

# ===== ATURAN PERSONA =====
PERSONAS = {
    "Asisten Ramah": "Kamu adalah asisten AI yang ramah. Jika menjelaskan matematika, SELALU gunakan format LaTeX ($...$). JANGAN PERNAH pakai tabel Markdown (| ... |) untuk rumus. Cukup gunakan list (poin-poin) atau paragraf biasa.",
    "Guru Matematika": "Kamu adalah guru matematika yang sabar. WAJIB pakai format LaTeX ($...$) untuk setiap rumus. JANGAN pakai tabel Markdown, cukup list atau paragraf.",
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

# ===== FUNGSI RENDER PESAN (DETEKSI RUMUS) =====
def render_pesan(teks, is_user=False):
    # Pisahkan teks berdasarkan $$...$$ (rumus blok)
    parts = re.split(r'(\$\$.*?\$\$)', teks, flags=re.DOTALL)
    
    for part in parts:
        if not part.strip(): continue
        
        # Jika bagian ini adalah rumus blok ($$ ... $$)
        if part.strip().startswith('$$') and part.strip().endswith('$$'):
            rumus = part.strip()[2:-2].strip()
            st.latex(rumus)
        else:
            # Jika teks biasa, render pakai markdown
            teks_html = markdown.markdown(part, extensions=['markdown.extensions.extra', 'markdown.extensions.nl2br'])
            teks_html = re.sub(r'(https?://\S+)', r'<a href="\1" target="_blank" style="color:#3B82F6; text-decoration:underline;">\1</a>', teks_html)
            
            if is_user:
                st.markdown(f'<div class="chat-row user"><div class="bubble">{teks_html}</div><div class="avatar" style="background-image: url(data:image/png;base64,{user_avatar_b64});"></div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-row ai"><div class="avatar" style="background-image: url(data:image/png;base64,{bot_avatar_b64});"></div><div class="bubble">{teks_html}</div></div>', unsafe_allow_html=True)


# ===== SIDEBAR KIRI =====
with st.sidebar:
    st.markdown("<h2 style='color:#3B82F6; display:flex; align-items:center; gap:10px; text-shadow: 0 0 10px rgba(59,130,246,0.5);'><span style='font-size:30px;'>✨</span> AI Chat</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6B7280; font-size:12px; margin-top:-15px;'>Your Smart Assistant</p>", unsafe_allow_html=True)
    
    if user_avatar_b64:
        st.markdown(f'<div style="display:flex; align-items:center; gap:10px; margin:20px 0; padding:10px; background:rgba(255,255,255,0.05); border-radius:12px;"><div style="width:40px; height:40px; border-radius:50%; background-image: url(data:image/png;base64,{user_avatar_b64}); background-size:cover; border: 2px solid #3B82F6;"></div><div><b>{user_email.split("@")[0]}</b><br><span style="font-size:10px; color:#6B7280;">Premium</span></div></div>', unsafe_allow_html=True)
    
    if st.button("➕ Chat Baru", use_container_width=True, type="primary"):
        bikin_chat_baru(); st.rerun()
        
    st.markdown("<div style='height:1px; background:#1F2937; margin:15px 0;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='color:#E5E7EB; font-weight:600; margin-bottom:10px;'>💬 Chat</p>", unsafe_allow_html=True)
    
    for chat_id, chat_data in st.session_state.conversations.items():
        is_active = (chat_id == st.session_state.current_id)
        label = f"{'🟢 ' if is_active else '▫️ '}{chat_data['title']}"
        if st.button(label, key=f"chat_{chat_id}", use_container_width=True):
            st.session_state.current_id = chat_id; st.rerun()
            
    st.markdown("<br>", unsafe_allow_html=True)
    st.selectbox("Pilih Kepribadian:", list(PERSONAS.keys()), key="persona")
    if st.button("Logout", use_container_width=True): st.logout()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(37,99,235,0.15) 0%, rgba(11,15,25,0.9) 100%); padding: 15px; border-radius: 15px; border: 1px solid rgba(37,99,235,0.3); margin-top: 20px;">
        <p style="color:#3B82F6; font-weight:bold; font-size:14px; margin-bottom:5px;">✨ Upgrade to Pro</p>
        <p style="font-size:10px; color:#9CA3AF; margin-bottom:10px;">Dapatkan fitur lebih lengkap.</p>
        <div style="background:#2563EB; text-align:center; padding:8px; border-radius:8px; color:white; font-size:12px; font-weight:bold; box-shadow: 0 0 10px rgba(37,99,235,0.4);">Upgrade</div>
    </div>
    """, unsafe_allow_html=True)

# ===== LAYOUT UTAMA (2 KOLOM: CHAT & PANEL KANAN) =====
col_chat, col_right = st.columns([2.5, 1])

with col_right:
    st.markdown("""
    <div class="ai-profile">
        <div class="ai-avatar-big">🤖</div>
        <h3 style="margin:0; color:white;">AI Assistant</h3>
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
                chat_aktif["messages"].append({
                    "role": "system", 
                    "content": f"Gunakan informasi dari dokumen berikut untuk menjawab pertanyaan user:\n\n{pdf_text[:10000]}" 
                })
                simpan_ke_file()
                st.success("PDF berhasil diproses!")
                st.rerun()

    st.markdown("<div style='height:1px; background:#1F2937; margin:15px 0;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6B7280; font-size:11px; font-weight:bold; text-transform:uppercase; margin-bottom:10px;'>Kemampuan</p>", unsafe_allow_html=True)
    
    fitur = [("💬", "Tanya Jawab", "Dapatkan jawaban cepat"), ("📄", "Rangkuman", "Ringkas informasi panjang"), ("💡", "Kreativitas", "Ide, tulisan, dan konsep"), ("💻", "Pemrograman", "Bantuan coding dan debugging"), ("📚", "Belajar", "Jelaskan topik apa saja")]
    for icon, title, desc in fitur:
        st.markdown(f'<div class="capability-item"><div style="font-size:20px; margin-right:10px; background:rgba(37,99,235,0.2); padding:8px; border-radius:10px; color:#3B82F6;">{icon}</div><div><p style="margin:0; font-weight:bold; font-size:13px; color:white;">{title}</p><p style="margin:0; font-size:10px; color:#9CA3AF;">{desc}</p></div></div>', unsafe_allow_html=True)
        
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(37,99,235,0.2) 0%, rgba(6,8,14,0) 100%); padding: 20px; border-radius: 15px; text-align:center; margin-top:20px; border: 1px solid rgba(37,99,235,0.2);">
        <p style="color:white; font-weight:bold; font-size:14px;">Bersama AI,<br>semua jadi lebih mudah!</p>
        <p style="font-size:30px; margin-top:10px;">😊</p>
    </div>
    """, unsafe_allow_html=True)

with col_chat:
    st.markdown(f'<div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #1F2937; margin-bottom:20px;"><div><h2 style="margin:0; color:white;">Chat dengan AI</h2><p style="margin:0; font-size:12px; color:#9CA3AF;">Tanya apa saja!</p></div><div style="display:flex; align-items:center; gap:8px; background:rgba(34,197,94,0.1); color:#22C55E; padding:5px 15px; border-radius:20px; font-size:12px; font-weight:bold; border:1px solid rgba(34,197,94,0.2); box-shadow: 0 0 10px rgba(34,197,94,0.2);"><div style="width:8px; height:8px; border-radius:50%; background:#22C55E;"></div> Online</div></div>', unsafe_allow_html=True)

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
