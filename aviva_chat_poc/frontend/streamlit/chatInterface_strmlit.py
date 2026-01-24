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

with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

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
        response = requests.post(
            "http://127.0.0.1:8000/chat",
            json={"user_message": prompt},
            timeout=60
        )
        response.raise_for_status()
        bot_reply = response.json().get("bot_response", "No response")
    except Exception as e:
        bot_reply = f"⚠️ Backend error: {e}"

    # 3️⃣ Show assistant response
    st.session_state.messages.append({
        "role": "assistant",
        "content": bot_reply
    })

    with chat_container:
        with st.chat_message("assistant"):
            st.markdown(bot_reply)
