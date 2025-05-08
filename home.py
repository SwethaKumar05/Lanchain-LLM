# main.py
import streamlit as st
import uuid

st.set_page_config(page_title="Task Platform Integration", layout="wide")

platforms = {
    "Asana": "asana",
    "Trello": "trello",
    "ClickUp": "clickup",
    "Linear": "linear",
    "Monday.com": "monday"
}

st.title("🔗 Connect to Task Platform")
selected = st.selectbox("Choose a platform to connect", list(platforms.keys()))

if st.button("Connect"):
    uuid_generated = str(uuid.uuid4())
    platform_key = platforms[selected]

    # Trigger platform login
    login_url = f"http://localhost:8080/{platform_key}/login?uuid={uuid_generated}"

    # Redirect to the Streamlit /chat page (located in pages/chat.py)
    redirect_url = f"http://localhost:8501/pages/chat?platform={platform_key}&uuid={uuid_generated}"

    st.success(f"Opening {selected} login... Please complete login and you will be redirected.")
    js = f"""
    window.open('{login_url}', '_blank');
    setTimeout(() => {{
        window.location.href = '{redirect_url}';
    }}, 5000);
    """
    st.components.v1.html(f"<script>{js}</script>", height=0)
