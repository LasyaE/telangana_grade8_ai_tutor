import streamlit as st
from datetime import datetime
from uuid import uuid4
from rag_engine import answer_question
from config import OLLAMA_MODEL

# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Telangana Grade 8 AI Tutor",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Blue educational theme
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --navy: #12345A;
        --blue: #1769AA;
        --blue-light: #EAF3FC;
        --ink: #172B4D;
        --muted: #66788A;
        --line: #DCE6F0;
    }
    .stApp {
        background: linear-gradient(180deg, #F7FAFE 0%, #FFFFFF 48%);
    }
    [data-testid="stSidebar"] {
        background: #F0F6FC;
        border-right: 1px solid #DCE6F0;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #12345A;
    }
    .hero {
        padding: 1.35rem 1.5rem;
        border-radius: 20px;
        background: linear-gradient(115deg, #12345A 0%, #1769AA 70%, #3D91CF 100%);
        color: white;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 24px rgba(18, 52, 90, 0.13);
    }
    .hero h1 {
        color: white;
        font-size: 2rem;
        margin: 0 0 .25rem 0;
        letter-spacing: -.4px;
    }
    .hero p {
        color: #E7F2FC;
        margin: 0;
        font-size: .98rem;
    }
    .section-label {
        color: #12345A;
        font-weight: 700;
        font-size: 1.05rem;
        margin: .8rem 0 .35rem 0;
    }
    .model-pill {
        display: inline-block;
        background: #E4F0FB;
        color: #174F80;
        border: 1px solid #C9DFF2;
        border-radius: 999px;
        padding: .28rem .65rem;
        font-size: .78rem;
        font-weight: 600;
    }
    .small-muted {
        color: #66788A;
        font-size: .84rem;
    }
    div.stButton > button {
        border-radius: 10px;
        border: 1px solid #C9DDF0;
        color: #174F80;
        background: white;
        font-weight: 600;
        transition: all .15s ease-in-out;
    }
    div.stButton > button:hover {
        border-color: #1769AA;
        color: #12345A;
        background: #F0F7FE;
    }
    div.stButton > button[kind="primary"] {
        background: #1769AA;
        border-color: #1769AA;
        color: white;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #12345A;
        border-color: #12345A;
        color: white;
    }
    [data-testid="stChatMessage"] {
        border: 1px solid #E2EAF2;
        border-radius: 15px;
        padding: .65rem .85rem;
        background: white;
        margin-bottom: .65rem;
    }
    [data-testid="stExpander"] {
        border: 1px solid #DCE6F0;
        border-radius: 12px;
        background: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

SUBJECTS = {
    "All subjects": "📚",
    "Mathematics": "➗",
    "Physical Sciences": "⚛️",
    "Biology": "🧬",
    "English": "📖",
    "Social Studies": "🌍",
}

QUICK_QUESTIONS = {
    "All subjects": [
        "What is photosynthesis?",
        "Why is the cell wall present in plant cells?",
        "What are rational numbers?",
        "What is the importance of forests?",
    ],
    "Mathematics": [
        "What are rational numbers?",
        "How do we compare two fractions?",
        "Explain the properties of integers.",
        "How do we calculate the area of a rectangle?",
    ],
    "Physical Sciences": [
        "What is force?",
        "Explain friction with examples.",
        "What are conductors and insulators?",
        "How is sound produced?",
    ],
    "Biology": [
        "What is photosynthesis?",
        "Why is the cell wall present in plant cells?",
        "What is the function of the human digestive system?",
        "Explain the importance of microorganisms.",
    ],
    "English": [
        "Summarise a lesson from the textbook.",
        "Explain the meaning of a poem.",
        "What is the central idea of a story?",
        "Explain the difficult words in a passage.",
    ],
    "Social Studies": [
        "What are the major functions of the government?",
        "Why are forests important?",
        "Explain the factors affecting agriculture.",
        "What is local self-government?",
    ],
}

if "conversations" not in st.session_state:
    first_id = str(uuid4())
    st.session_state.conversations = [{
        "id": first_id,
        "title": "New chat",
        "created_at": datetime.now().strftime("%d %b, %I:%M %p"),
        "messages": [],
    }]
    st.session_state.active_chat_id = first_id

if "pending_question" not in st.session_state:
    st.session_state.pending_question = ""
if "subject_choice" not in st.session_state:
    st.session_state.subject_choice = "All subjects"
if "marks_choice" not in st.session_state:
    st.session_state.marks_choice = 4


def get_active_chat():
    for conversation in st.session_state.conversations:
        if conversation["id"] == st.session_state.active_chat_id:
            return conversation
    return st.session_state.conversations[-1]


def create_new_chat():
    new_id = str(uuid4())
    st.session_state.conversations.insert(0, {
        "id": new_id,
        "title": "New chat",
        "created_at": datetime.now().strftime("%d %b, %I:%M %p"),
        "messages": [],
    })
    st.session_state.active_chat_id = new_id
    st.session_state.pending_question = ""


def submit_question(question, subject, marks):
    question = question.strip()
    if not question:
        return

    chat = get_active_chat()
    if chat["title"] == "New chat":
        chat["title"] = question[:42] + ("…" if len(question) > 42 else "")

    message = {
        "question": question,
        "subject": subject,
        "marks": marks,
        "answer": None,
        "sources": [],
        "error": None,
    }
    chat["messages"].append(message)

    try:
        with st.spinner("Searching your textbook and preparing your exam-ready answer..."):
            answer, sources = answer_question(question, subject, marks)
        message["answer"] = answer
        message["sources"] = sources
    except Exception as exc:
        message["error"] = str(exc)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("## 📘 Grade 8 AI Tutor")
    st.caption("Telangana State Board • Class VIII")
    st.markdown("---")

    if st.button("＋  New chat", type="primary", use_container_width=True):
        create_new_chat()
        st.rerun()

    st.markdown("### 📚 Choose a subject")
    selected_subject = st.selectbox(
        "Subject",
        options=list(SUBJECTS.keys()),
        format_func=lambda value: f"{SUBJECTS[value]}  {value}",
        key="subject_choice",
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 🕘 Chat history")
    if not st.session_state.conversations:
        st.caption("Your conversations will appear here.")

    for conversation in st.session_state.conversations[:12]:
        label = conversation["title"]
        if conversation["id"] == st.session_state.active_chat_id:
            label = "●  " + label
        if st.button(
            label,
            key=f"history_{conversation['id']}",
            use_container_width=True,
            help=conversation["created_at"],
        ):
            st.session_state.active_chat_id = conversation["id"]
            st.session_state.pending_question = ""
            st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Tutor information")
    st.markdown(
        f'<span class="model-pill">● Local model: {OLLAMA_MODEL}</span>',
        unsafe_allow_html=True,
    )
    st.caption("Answers use the currently indexed textbook passages.")
    st.caption("Chat history is temporary and lasts only for this app session.")

# ---------------------------------------------------------
# Main page header
# ---------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>📘 Telangana Grade 8 AI Tutor</h1>
        <p>Ask questions, understand concepts and prepare exam-ready answers.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

active_chat = get_active_chat()

if not active_chat["messages"]:
    st.markdown("### 👋 Hello, student!")
    st.write("What would you like to learn today?")
    st.markdown(
        f'<span class="model-pill">{SUBJECTS[selected_subject]} {selected_subject}</span>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">✨ Quick questions</div>', unsafe_allow_html=True)
    quick_questions = QUICK_QUESTIONS[selected_subject]
    cols = st.columns(2)
    for index, quick_question in enumerate(quick_questions):
        with cols[index % 2]:
            if st.button(
                quick_question,
                key=f"quick_{active_chat['id']}_{index}",
                use_container_width=True,
            ):
                st.session_state.pending_question = quick_question
                st.rerun()
else:
    st.markdown("### Conversation")
    for message in active_chat["messages"]:
        with st.chat_message("user"):
            st.write(message["question"])
            st.caption(
                f"{SUBJECTS[message['subject']]} {message['subject']} · "
                f"{message['marks']} marks"
            )

        with st.chat_message("assistant", avatar="📘"):
            if message["error"]:
                st.error(f"Could not answer: {message['error']}")
                st.caption(
                    "Check that Ollama is running, the configured model is available, "
                    "and the ChromaDB index has been built."
                )
            elif message["answer"] is not None:
                st.markdown(message["answer"])

                # Show only unique subject and page-number references.
                if message["sources"]:
                    unique_pages = []
                    seen_pages = set()
                    for hit in message["sources"]:
                        metadata = hit["metadata"]
                        subject_name = metadata.get("subject", message["subject"])
                        page = metadata.get("page")
                        key = (subject_name, str(page))
                        if page is not None and key not in seen_pages:
                            seen_pages.add(key)
                            unique_pages.append(key)

                    if unique_pages:
                        with st.expander("📚 Textbook references"):
                            for subject_name, page in unique_pages:
                                st.markdown(
                                    f"- {SUBJECTS.get(subject_name, '📘')} "
                                    f"{subject_name} · Page {page}"
                                )
            else:
                st.info("Preparing your answer...")

# ---------------------------------------------------------
# Answer format selector and chat input
# ---------------------------------------------------------
st.markdown("### 📝 Answer format")
marks_choice = st.radio(
    "Select the marks for your answer",
    options=[2, 4, 8],
    format_func=lambda value: {
        2: "2 marks · Short",
        4: "4 marks · Detailed",
        8: "8 marks · Comprehensive",
    }[value],
    horizontal=True,
    key="marks_choice",
)

prompt = st.chat_input("Ask a question from your Class 8 textbook...")
question_to_process = prompt or st.session_state.pending_question

if question_to_process:
    st.session_state.pending_question = ""
    submit_question(question_to_process, selected_subject, marks_choice)
    st.rerun()

st.markdown(
    "<p class='small-muted' style='text-align:center; margin-top:1.2rem;'>"
    "Telangana State Board • Class VIII • Textbook-grounded exam preparation assistant"
    "</p>",
    unsafe_allow_html=True,
)
