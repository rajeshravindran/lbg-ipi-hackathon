import streamlit as st
import requests

# -----------------------
# Page config
# -----------------------
st.set_page_config(
    page_title="AI Chatbot",
    page_icon="💬",
    layout="centered"
)

st.title("💬 AI Chatbot")

# -----------------------
# Initialize chat history
# -----------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------
# Chat container (your "div")
# -----------------------
chat_container = st.container(height=450)

# -----------------------
# Chat input (fixed bottom)
# -----------------------
prompt = st.chat_input("Type your message...")

if prompt:
    # 1️⃣ Show user message immediately
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

    # 2️⃣ Call FastAPI backend
    try:
        payload = {"user_message": prompt}
        
        response = requests.post(
            "http://127.0.0.1:8000/chat",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        bot_reply = response.json().get("bot_response", "No response")
        with chat_container:
            with st.chat_message("Bot"):
                st.markdown(bot_reply)
    except requests.exceptions.HTTPError as e:
        bot_reply = f"⚠️ HTTP Error: {e}\nResponse: {e.response.text}"  # Show full error
    except Exception as e:
        bot_reply = f"⚠️ Backend error: {e}"
