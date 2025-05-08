import os
import uuid
import requests
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Set up LLM & Embedding
llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY)
embedding = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)

# Streamlit Setup
st.set_page_config(page_title="Task Chat | RAG + Gemini", layout="wide")

# Supported Platforms
platforms = {
    "Asana": "asana",
    "Trello": "trello",
    "ClickUp": "clickup",
    "Linear": "linear",
    "Monday.com": "monday"
}

# Get query params
query_params = st.query_params
uuid_param = query_params.get("uuid", None)
platform_param = query_params.get("platform", None)
page = query_params.get("page", "login")

# -----------------------------------
# Page 1: Platform Login
# -----------------------------------
if page == "login":
    st.title("🔗 Connect to Task Platform")

    selected = st.selectbox("Choose a platform to connect", list(platforms.keys()))

    if st.button("Connect"):
        uuid_generated = str(uuid.uuid4())
        platform_key = platforms[selected]

        st.session_state["uuid"] = uuid_generated
        st.session_state["platform"] = platform_key

        login_url = f"http://localhost:8080/{platform_key}/login?uuid={uuid_generated}"

        st.success(f"Click below to log in to {selected}")
        st.markdown(f"[🔐 Login to {selected}]({login_url})", unsafe_allow_html=True)

        st.markdown("After completing the login, click below to proceed to chat:")
        if st.button("➡️ Go to Chat"):
            st.query_params["page"] = "chat"
            st.query_params["uuid"] = uuid_generated
            st.query_params["platform"] = platform_key
            st.rerun()


# -----------------------------------
# Page 2: Chat with RAG
# -----------------------------------
elif page == "chat" and uuid_param and platform_param:
    st.title("💬 Chat with Your Tasks")

    endpoint = f"http://localhost:8080/{platform_param}/get-data?uuid={uuid_param}"
    response = requests.get(endpoint)

    if response.status_code != 200:
        st.error("❌ Failed to fetch task data.")
        st.stop()

    data = response.json()
    st.success("✅ Task data retrieved successfully.")

    with st.expander("📦 Raw Data (Debug)", expanded=False):
        st.json(data)

    # 🧠 RAG Step 1: Extract text
    def extract_chunks(data, platform):
        chunks = []
        if platform == "asana":
            for project in data.get("asana_data", []):
                chunks.append(f"Project: {project['project']['name']}")
                for section in project["sections"]:
                    chunks.append(f"Section: {section['name']}")
                for task in project["tasks"]:
                    chunks.append(f"Task: {task['name']}, Completed: {task.get('completed')}")
        # Add more platforms later
        return chunks

    task_chunks = extract_chunks(data, platform_param)
    documents = [Document(page_content=chunk) for chunk in task_chunks]

    # 🧠 RAG Step 2: Build vectorstore
    vectorstore = FAISS.from_documents(documents, embedding)
    qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=vectorstore.as_retriever())

    # 🧠 RAG Step 3: Question interface
    st.markdown("#### Ask anything about your tasks:")
    question = st.text_input("Type your question here...", placeholder="E.g., What are the incomplete tasks?")

    if question:
        with st.spinner("Thinking..."):
            response = qa_chain.run(question)
            st.markdown("### 🤖 Answer")
            st.success(response)
