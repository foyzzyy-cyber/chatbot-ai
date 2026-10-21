import streamlit as st
from groq import Groq
import uuid
import json
from pypdf import PdfReader
import os
import requests
from bs4 import BeautifulSoup
import markdown

# ===== KONFIGURASI HALAMAN =====
st.set_page_config(
    page_title="Chatbot Saya",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ===== CSS CUSTOM =====
st.markdown("""
<style>
    .chat-user { display: flex; justify-content: flex-end; gap: 10px; margin-bottom: 15px; }
    .chat-user .bubble { background-color: #A855F7; color: white; padding: 10px 15px; border-radius: 15px 15px 0px 15px; max-width: 75%; }
    .chat-ai { display: flex; justify-content: flex-start; gap: 10px; margin-bottom: 15px; }
    .chat-ai .bubble { background-color: #2D2D2D; color: #E0E0E0; padding: 10px 15px; border-radius: 15px 15px 15px 0px; max-width: 75%; }
    .avatar { width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; background-color: #444; }
    .welcome-container { text-align: center; margin-top: 50px; color: #888; }
    .welcome-container h1 { color: #A855F7; font-size: 3em; }
</style>
""", unsafe_allow_html=True)

# ===== SETUP API & LOGIN =====
client = Groq(api_key=st.secrets["GROQ_API_KEY"])   

if not st.user.is_logged_in:
    st.title("🤖 Chatbot AI Portofolio")
    st.write("Silakan login untuk mulai menggunakan chatbot.")
    if st.button("Login with Google", type="primary"):
        st.login()
    st.stop()

user_email = st.user.email
folder_user = f"data_{user_email.replace('@', '_').replace('.', '_')}"
os.makedirs(folder_user, exist_ok=True)
FILE_DB = os.path.join(folder_user, "chats.json")

# Daftar kepribadian AI
PERSONAS = {
    "Asisten Ramah": "Kamu adalah Chatbot Saya, asisten AI yang ramah, suka bercanda, dan membantu.",
    "Guru Matematika": "Kamu adalah guru matematika yang sabar. Jelaskan konsep dengan langkah-langkah sederhana dan contoh.",
    "Koki Profesional": "Kamu adalah koki profesional. Bantu user dengan resep, tips memasak, dan bahan pengganti.",
    "Programmer Expert": "Kamu adalah senior programmer. Bantu user debugging dan jelaskan kode dengan bahasa yang mudah dipahami."
}

def get_system_prompt():
    return PERSONAS[st.session_state.get("persona", "Asisten Ramah")]

# ===== FUNGSI SIMPAN & MUAT =====
def simpan_ke_file():
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(st.session_state.conversations, f, ensure_ascii=False, indent=2)

def muat_dari_file():
    if os.path.exists(FILE_DB):
        with open(FILE_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

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
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator=' ', strip=True)
        return text[:15000]
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
    data_lama = muat_dari_file()
    st.session_state.conversations = data_lama if data_lama else {}

if "current_id" not in st.session_state:
    if st.session_state.conversations:
        st.session_state.current_id = list(st.session_state.conversations.keys())[0]
    else:
        bikin_chat_baru()

# ===== SIDEBAR =====
with st.sidebar:
    st.title("💬 Percakapan")
    st.caption(f"Login: **{user_email}**")
    
    if st.button("Logout", use_container_width=True):
        st.logout()
    
    st.markdown("---")
    st.selectbox("Pilih Kepribadian AI:", list(PERSONAS.keys()), key="persona")
    st.markdown("---")
    
    if st.button("➕ Chat Baru", use_container_width=True, type="primary"):
        bikin_chat_baru()
        st.rerun()
    
    st.markdown("---")
    
    for chat_id, chat_data in st.session_state.conversations.items():
        is_active = (chat_id == st.session_state.current_id)
        label = f"{'🟢 ' if is_active else '▫️ '}{chat_data['title']}"
        if st.button(label, key=f"chat_{chat_id}", use_container_width=True):
            st.session_state.current_id = chat_id
            st.rerun()
    
    st.markdown("---")
    
    if len(st.session_state.conversations) > 1:
        if st.button("🗑️ Hapus Chat Ini", use_container_width=True):
            del st.session_state.conversations[st.session_state.current_id]
            st.session_state.current_id = list(st.session_state.conversations.keys())[0]
            simpan_ke_file()
            st.rerun()

    st.markdown("---")
    
    chat_aktif = ambil_chat_aktif()
    teks_chat = "".join([f"{msg['role'].upper()}: {msg['content']}\n\n" for msg in chat_aktif["messages"] if msg["role"] != "system"])
    
    st.download_button(
        label="📥 Download Chat (TXT)",
        data=teks_chat,
        file_name=f"chat_{chat_aktif['title']}.txt",
        mime="text/plain",
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("📄 Upload Dokumen")
    uploaded_file = st.file_uploader("Pilih file PDF", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("Proses PDF", use_container_width=True):
            with st.spinner("Membaca PDF..."):
                pdf_text = extract_text_from_pdf(uploaded_file)
                chat_aktif["messages"].append({
                    "role": "system", 
                    "content": f"Gunakan informasi dari dokumen berikut untuk menjawab pertanyaan user:\n\n{pdf_text[:10000]}" 
                })
                simpan_ke_file()
                st.success("PDF berhasil diproses!")
                st.rerun()

    st.markdown("---")
    st.subheader("🌐 Baca dari Link")
    url_input = st.text_input("Masukkan URL artikel:")
    
    if st.button("Proses Link", use_container_width=True):
        if url_input:
            with st.spinner("Membaca web..."):
                teks_web = ambil_teks_dari_url(url_input)
                chat_aktif["messages"].append({
                    "role": "system", 
                    "content": f"Gunakan informasi dari web berikut untuk menjawab pertanyaan user:\n\n{teks_web}"
                })
                simpan_ke_file()
                st.success("Link berhasil diproses! Silakan tanya sesuatu tentang isi web.")
                st.rerun()
        else:
            st.warning("Masukkan URL dulu ya.")

# ===== AREA CHAT =====
chat = ambil_chat_aktif()

if chat["messages"][0]["role"] == "system":
    chat["messages"][0]["content"] = get_system_prompt()

# Cek kalau chat masih kosong (baru dibuat), tampilkan Welcome Screen
if len(chat["messages"]) == 1:
    st.markdown("""
    <div class="welcome-container">
        <h1>👋 Selamat Datang!</h1>
        <p>Aku adalah asisten AI kamu. Silakan tanya apa aja, upload PDF, atau masukin link artikel.</p>
        <p>Coba ketik sesuatu di kolom bawah untuk memulai! 🚀</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.title(f"🤖 {chat['title']}")
    st.caption("Tanya apa aja, aku siap bantu!")

    # Tampilkan history
    for p in chat["messages"]:
        if p["role"] == "system": continue
        teks_html = markdown.markdown(p["content"])
        if p["role"] == "user":
            st.markdown(f'<div class="chat-user"><div class="bubble">{teks_html}</div><div class="avatar">🧑</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-ai"><div class="avatar">🤖</div><div class="bubble">{teks_html}</div></div>', unsafe_allow_html=True)

# Input user
user = st.chat_input("Ketik pesan...")

if user:
    if len(chat["messages"]) == 1:
        chat["title"] = user[:30] + ("..." if len(user) > 30 else "")
    
    chat["messages"].append({"role": "user", "content": user})
    teks_html_user = markdown.markdown(user)
    st.markdown(f'<div class="chat-user"><div class="bubble">{teks_html_user}</div><div class="avatar">🧑</div></div>', unsafe_allow_html=True)

    with st.spinner("AI sedang mengetik..."):
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
