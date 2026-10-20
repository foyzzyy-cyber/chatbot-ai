import streamlit as st
from groq import Groq
import uuid
import json
from pypdf import PdfReader
import os

# ===== KONFIGURASI HALAMAN =====
st.set_page_config(
    page_title="Chatbot Saya",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ===== CSS CUSTOM (Rata Kanan-Kiri) =====
st.markdown("""
<style>
    /* Container chat */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 15px;
        margin-bottom: 20px;
    }
    
    /* Bubble User (Kanan) */
    .chat-user {
        display: flex;
        justify-content: flex-end;
        align-items: flex-start;
        gap: 10px;
    }
    .chat-user .bubble {
        background-color: #A855F7; /* Warna ungu tema kamu */
        color: white;
        padding: 12px 16px;
        border-radius: 15px 15px 0px 15px; /* Sudut melengkung */
        max-width: 75%;
        word-wrap: break-word;
    }
    
    /* Bubble AI (Kiri) */
    .chat-ai {
        display: flex;
        justify-content: flex-start;
        align-items: flex-start;
        gap: 10px;
    }
    .chat-ai .bubble {
        background-color: #2D2D2D; /* Warna abu gelap */
        color: #E0E0E0;
        padding: 12px 16px;
        border-radius: 15px 15px 15px 0px;
        max-width: 75%;
        word-wrap: break-word;
    }
    
    /* Avatar */
    .avatar {
        width: 35px;
        height: 35px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        background-color: #444;
    }
</style>
""", unsafe_allow_html=True)

# ===== SETUP API =====
client = Groq(api_key=st.secrets["GROQ_API_KEY"])   

# Daftar kepribadian AI
PERSONAS = {
    "Asisten Ramah": "Kamu adalah Chatbot Saya, asisten AI yang ramah, suka bercanda, dan membantu.",
    "Guru Matematika": "Kamu adalah guru matematika yang sabar. Jelaskan konsep dengan langkah-langkah sederhana dan contoh.",
    "Koki Profesional": "Kamu adalah koki profesional. Bantu user dengan resep, tips memasak, dan bahan pengganti.",
    "Programmer Expert": "Kamu adalah senior programmer. Bantu user debugging dan jelaskan kode dengan bahasa yang mudah dipahami."
}

def get_system_prompt():
    persona_pilihan = st.session_state.get("persona", "Asisten Ramah")
    return PERSONAS[persona_pilihan]

# ===== FUNGSI SIMPAN & MUAT =====
FILE_DB = "chats.json"

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
    
    st.selectbox(
        "Pilih Kepribadian AI:", 
        list(PERSONAS.keys()), 
        key="persona"
    )
    
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

    st.markdown("---")

    st.subheader("📄 Upload Dokumen")
    uploaded_file = st.file_uploader("Pilih file PDF", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("Proses PDF", use_container_width=True):
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

# ===== AREA CHAT =====
chat = ambil_chat_aktif()

if chat["messages"][0]["role"] == "system":
    chat["messages"][0]["content"] = get_system_prompt()

st.title(f"🤖 {chat['title']}")
st.caption("Tanya apa aja, aku siap bantu!")

# Tampilkan history pakai Custom HTML
for p in chat["messages"]:
    if p["role"] == "system":
        continue
        
    if p["role"] == "user":
        # Tampilan Pesan User (Kanan)
        st.markdown(f"""
        <div class="chat-user">
            <div class="bubble">{p["content"]}</div>
            <div class="avatar">🧑</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Tampilan Pesan AI (Kiri)
        st.markdown(f"""
        <div class="chat-ai">
            <div class="avatar">🤖</div>
            <div class="bubble">{p["content"]}</div>
        </div>
        """, unsafe_allow_html=True)

# Input user
user = st.chat_input("Ketik pesan...")

if user:
    if len(chat["messages"]) == 1:
        chat["title"] = user[:30] + ("..." if len(user) > 30 else "")
    
    chat["messages"].append({"role": "user", "content": user})
    
    # Tampilkan pesan user langsung
    st.markdown(f"""
    <div class="chat-user">
        <div class="bubble">{user}</div>
        <div class="avatar">🧑</div>
    </div>
    """, unsafe_allow_html=True)

    # Minta jawaban AI
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
                st.rerun() # Refresh biar format HTML-nya bener
            else:
                st.warning("⚠️ AI tidak mengembalikan teks. Coba lagi.")
                
        except Exception as e:
            st.error(f"⚠️ Error: {e}")
