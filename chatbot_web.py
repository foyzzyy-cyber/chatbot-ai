import streamlit as st
from groq import Groq
import uuid
import json
import os

# ===== KONFIGURASI HALAMAN =====
st.set_page_config(
    page_title="Chatbot Saya",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ===== SETUP API =====
client = Groq(api_key=st.secrets["GROQ_API_KEY"])   

# Daftar kepribadian AI
PERSONAS = {
    "Asisten Ramah": "Kamu adalah Chatbot Saya, asisten AI yang ramah, suka bercanda, dan membantu.",
    "Guru Matematika": "Kamu adalah guru matematika yang sabar. Jelaskan konsep dengan langkah-langkah sederhana dan contoh.",
    "Koki Profesional": "Kamu adalah koki profesional. Bantu user dengan resep, tips memasak, dan bahan pengganti.",
    "Programmer Expert": "Kamu adalah senior programmer. Bantu user debugging dan jelaskan kode dengan bahasa yang mudah dipahami."
}

# Fungsi buat dapetin system prompt berdasarkan pilihan
def get_system_prompt():
    persona_pilihan = st.session_state.get("persona", "Asisten Ramah")
    return PERSONAS[persona_pilihan]

# ===== FUNGSI SIMPAN & MUAT =====
FILE_DB = "chats.json"

def simpan_ke_file():
    """Simpan semua percakapan ke file JSON."""
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(st.session_state.conversations, f, ensure_ascii=False, indent=2)

def muat_dari_file():
    """Muat percakapan dari file JSON kalau ada."""
    if os.path.exists(FILE_DB):
        with open(FILE_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# ===== FUNGSI BANTU =====
def bikin_chat_baru():
    """Bikin percakapan baru, return ID-nya."""
    new_id = str(uuid.uuid4())[:8]   # ID unik 8 karakter
    st.session_state.conversations[new_id] = {
        "title": "Chat Baru",
        "messages": [{"role": "system", "content": get_system_prompt()}]
    }
    st.session_state.current_id = new_id
    simpan_ke_file() # <--- AUTO SAVE SAAT BIKIN CHAT BARU

def ambil_chat_aktif():
    """Ambil data percakapan yang lagi aktif."""
    return st.session_state.conversations[st.session_state.current_id]

# ===== INISIALISASI STATE =====
if "conversations" not in st.session_state:
    data_lama = muat_dari_file()
    if data_lama:
        st.session_state.conversations = data_lama
    else:
        st.session_state.conversations = {}

if "current_id" not in st.session_state:
    if st.session_state.conversations:
        st.session_state.current_id = list(st.session_state.conversations.keys())[0]
    else:
        bikin_chat_baru()

# ===== SIDEBAR =====
with st.sidebar:
    st.title("💬 Percakapan")
    
    # Dropdown Ganti Persona
    st.selectbox(
        "Pilih Kepribadian AI:", 
        list(PERSONAS.keys()), 
        key="persona"
    )
    
    st.markdown("---")
    
    # Tombol chat baru
    if st.button("➕ Chat Baru", use_container_width=True, type="primary"):
        bikin_chat_baru()
        st.rerun()
    
    st.markdown("---")
    
    # Daftar semua percakapan
    for chat_id, chat_data in st.session_state.conversations.items():
        is_active = (chat_id == st.session_state.current_id)
        label = f"{'🟢 ' if is_active else '▫️ '}{chat_data['title']}"
        if st.button(label, key=f"chat_{chat_id}", use_container_width=True):
            st.session_state.current_id = chat_id
            st.rerun()
    
    st.markdown("---")
    
    # Tombol hapus chat aktif
    if len(st.session_state.conversations) > 1:
        if st.button("🗑️ Hapus Chat Ini", use_container_width=True):
            del st.session_state.conversations[st.session_state.current_id]
            st.session_state.current_id = list(st.session_state.conversations.keys())[0]
            simpan_ke_file() # <--- AUTO SAVE SAAT HAPUS CHAT
            st.rerun()

    st.markdown("---")
    
    # Tombol Export Chat
    chat_aktif = ambil_chat_aktif()
    teks_chat = ""
    for msg in chat_aktif["messages"]:
        if msg["role"] != "system":
            teks_chat += f"{msg['role'].upper()}: {msg['content']}\n\n"
    
    st.download_button(
        label="📥 Download Chat (TXT)",
        data=teks_chat,
        file_name=f"chat_{chat_aktif['title']}.txt",
        mime="text/plain",
        use_container_width=True
    )

# ===== AREA CHAT =====
chat = ambil_chat_aktif()

# Update system prompt kalau user ganti persona
if chat["messages"][0]["role"] == "system":
    chat["messages"][0]["content"] = get_system_prompt()

st.title(f"🤖 {chat['title']}")
st.caption("Tanya apa aja, aku siap bantu!")

# Tampilkan history
for p in chat["messages"]:
    if p["role"] == "system":
        continue
    avatar = "🧑" if p["role"] == "user" else "🤖"
    with st.chat_message(p["role"], avatar=avatar):
        st.write(p["content"])

# Input user
user = st.chat_input("Ketik pesan...")

if user:
    # Kalau ini pesan pertama, jadikan judul chat
    if len(chat["messages"]) == 1:
        chat["title"] = user[:30] + ("..." if len(user) > 30 else "")
    
    # Tampilkan pesan user
    chat["messages"].append({"role": "user", "content": user})
    with st.chat_message("user", avatar="🧑"):
        st.write(user)
    
    # Minta jawaban AI (STREAMING)
    with st.chat_message("assistant", avatar="🤖"):
        try:
            # Tambahkan stream=True
            stream = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=chat["messages"],
                stream=True 
            )
            
            def generate_chunks():
                for chunk in stream:
                    # Cek yang lebih aman buat nampilin teks
                    if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            
            # Tampilkan dengan efek ngetik
            jawab = st.write_stream(generate_chunks())
            
            # Simpan jawaban utuh ke history
            if jawab:
                chat["messages"].append({"role": "assistant", "content": jawab})
                simpan_ke_file()
            else:
                st.warning("⚠️ AI tidak mengembalikan teks. Coba lagi.")
                
        except Exception as e:
            st.error(f"⚠️ Error: {e}")
