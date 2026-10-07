import asyncio
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().with_name(".env"))

import streamlit as st
from fastapi import HTTPException
from streamlit.errors import StreamlitSecretNotFoundError

from backend.main import ChatMessage, fetch_repository_context, generate_answer, parse_repository_url


SUGGESTED_QUESTIONS = (
    "What does this project do?",
    "How do I run it locally?",
    "Where should I start reading the code?",
)

def get_openrouter_api_key() -> str:
    environment_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if environment_key:
        return environment_key
    try:
        return str(st.secrets["OPENROUTER_API_KEY"]).strip()
    except (KeyError, StreamlitSecretNotFoundError):
        return ""


async def answer_repository_question(
    repository_url: str,
    question: str,
    history: list[ChatMessage],
    api_key: str,
) -> tuple[str, str]:
    owner, repository_name = parse_repository_url(repository_url)
    async with httpx.AsyncClient(
        timeout=20.0, headers={"Accept": "application/vnd.github+json"}
    ) as github_client:
        full_name, context = await fetch_repository_context(
            github_client, owner, repository_name, question
        )
    answer = await generate_answer(api_key, full_name, context, question, history)
    return full_name, answer


def use_suggested_question(question: str) -> None:
    st.session_state.pending_question = question


st.set_page_config(page_title="RepoGuide", page_icon="✳", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root {
      color-scheme: light;
      --ink: #202923;
      --muted: #747e77;
      --green: #457b5d;
      --green-dark: #315e46;
      --green-pale: #e9f2eb;
      --line: #e6eae5;
      --paper: #fbfcfa;
    }
    .stApp {
      background: radial-gradient(ellipse at 50% 0%, rgba(232,241,232,.72), transparent 34rem), var(--paper);
      color: var(--ink);
      font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"] { background: transparent; }
    [data-testid="stMainBlockContainer"] { max-width: 920px; padding-top: 1rem; }
    h1, h2, h3 { color: var(--ink); font-family: 'Manrope', sans-serif; letter-spacing: -.045em; }
    .brandbar {
      display:flex; align-items:center; justify-content:space-between;
      padding: 5px 0 18px; border-bottom:1px solid rgba(215,224,216,.8);
      color:var(--muted); font-size:12px;
    }
    .brandmark {
      display:inline-grid; place-items:center; width:29px; height:29px; margin-right:9px;
      border-radius:9px; background:var(--green); color:white;
      font-family:'Manrope',sans-serif; font-weight:800;
    }
    .brandname { color:var(--ink); font-size:15px; font-weight:700; letter-spacing:-.04em; }
    .hero { padding:34px 0 22px; text-align:center; }
    .eyebrow {
      color:var(--green); font-family:'DM Mono',monospace; font-size:10px;
      letter-spacing:.13em; text-transform:uppercase;
    }
    .hero h1 { margin:12px 0 8px; font-size:clamp(38px,6vw,56px); line-height:1.05; }
    .hero h1 span { color:var(--green); }
    .hero p { margin:0; color:var(--muted); font-size:14px; }
    .repo-label {
      margin:0 0 8px 2px; color:#5b675e; font-family:'DM Mono',monospace;
      font-size:10px; letter-spacing:.09em; text-transform:uppercase;
    }
    div[data-testid="stForm"] {
      padding:14px 16px 10px; border:1px solid #dce5dc; border-radius:13px;
      background:white; box-shadow:0 5px 20px rgba(42,65,48,.035);
    }
    div[data-testid="stTextInput"] input {
      min-height:43px; border-color:#e6eae5; border-radius:9px; background:#fff;
    }
    div[data-testid="stButton"] button, div[data-testid="stFormSubmitButton"] button {
      min-height:42px; border:1px solid var(--green); border-radius:9px;
      background:var(--green); color:#fff; font-weight:600;
    }
    div[data-testid="stButton"] button:hover, div[data-testid="stFormSubmitButton"] button:hover {
      border-color:var(--green-dark); background:var(--green-dark); color:#fff;
    }
    .privacy-note { margin:8px 2px 18px; color:#929b93; font-size:11px; }
    .assistant-card {
      display:flex; align-items:center; gap:11px; margin-top:7px; padding:14px 17px;
      border:1px solid var(--line); border-radius:14px 14px 0 0; background:white;
    }
    .assistant-icon {
      display:grid; place-items:center; width:35px; height:35px; border-radius:11px;
      background:var(--green-pale); color:var(--green); font-size:21px;
    }
    .assistant-title { color:var(--ink); font-size:13px; font-weight:700; }
    .assistant-status { margin-top:2px; color:var(--muted); font-size:11px; }
    .online-dot { width:7px; height:7px; margin-left:auto; border-radius:50%; background:#6eaa7e; }
    .chat-panel {
      min-height:225px; padding:15px 19px 9px; border:1px solid var(--line);
      border-top:0; border-radius:0 0 14px 14px; background:white;
      box-shadow:0 13px 38px rgba(37,56,42,.045);
    }
    .welcome { padding:21px 8px 17px; text-align:center; }
    .welcome-icon { color:#76a982; font-size:23px; }
    .welcome-title { margin:6px 0; color:var(--ink); font-family:'Manrope',sans-serif; font-size:18px; font-weight:700; }
    .welcome-copy { max-width:440px; margin:0 auto; color:var(--muted); font-size:12px; line-height:1.6; }
    .chat-footnote { margin:8px 0 0; color:#929b93; text-align:center; font-size:10px; }
    div[data-testid="stChatMessage"] { padding:9px 12px; }
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
      border-radius:12px 12px 4px 12px; background:var(--green); color:white;
    }
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
      border:1px solid #e9eee9; border-radius:12px 12px 12px 4px; background:#fbfcfa;
    }
    div[data-testid="stChatInput"] {
      border-color:#e1e8e1; border-radius:12px; background:#fff;
      box-shadow:0 5px 20px rgba(42,65,48,.035);
    }
    footer { visibility:hidden; }
    @media(max-width:640px) {
      [data-testid="stMainBlockContainer"] { padding: .5rem 1rem 2rem; }
      .hero { padding-top:26px; }
      .brandbar { font-size:10px; }
      .chat-panel { padding:12px 10px 7px; }
    }
    </style>
    <div class="brandbar"><div><span class="brandmark">R</span><span class="brandname">RepoGuide</span></div><span>A little guide to any public repo</span></div>
    <section class="hero"><div class="eyebrow">✳ &nbsp; YOUR REPOSITORY, EXPLAINED</div><h1>Get to know<br><span>any codebase.</span></h1><p>Drop in a public GitHub repo and ask what you’ve always wanted to know.</p></section>
    """,
    unsafe_allow_html=True,
)

if "repository_url" not in st.session_state:
    st.session_state.repository_url = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown('<div class="repo-label">Public GitHub repository</div>', unsafe_allow_html=True)
with st.form("repository-form"):
    repo_column, action_column = st.columns([5, 1.35], vertical_alignment="center")
    with repo_column:
        repository_input = st.text_input(
            "Repository URL",
            label_visibility="collapsed",
            value=st.session_state.repository_url,
            placeholder="https://github.com/owner/repository",
        )
    with action_column:
        connect_repository = st.form_submit_button(
            "Connect repo ↗", use_container_width=True
        )

if connect_repository:
    try:
        owner, repository_name = parse_repository_url(repository_input)
    except HTTPException as error:
        st.error(error.detail)
    else:
        st.session_state.repository_url = f"https://github.com/{owner}/{repository_name}"
        st.session_state.repository_name = f"{owner}/{repository_name}"
        st.session_state.messages = []
        st.rerun()

connected = bool(st.session_state.repository_url)
status = st.session_state.get("repository_name", "Ready when you are")
st.markdown(
    f"""
    <div class="privacy-note">Public repositories only. Your API key stays private.
    {f" &nbsp; · &nbsp; Connected to <strong>{status}</strong>" if connected else ""}</div>
    <div class="assistant-card"><div class="assistant-icon">✳</div>
    <div><div class="assistant-title">Repository assistant</div>
    <div class="assistant-status">{status}</div></div><span class="online-dot"></span></div>
    <div class="chat-panel">
      {"" if st.session_state.messages else '<div class="welcome"><div class="welcome-icon">✳</div><div class="welcome-title">Let’s explore something.</div><div class="welcome-copy">Connect a repository above, then ask about its code, structure, or how to get started.</div></div>'}
    </div>
    """,
    unsafe_allow_html=True,
)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if connected and not st.session_state.messages:
    suggestion_columns = st.columns(3)
    for column, suggestion in zip(suggestion_columns, SUGGESTED_QUESTIONS):
        with column:
            st.button(
                suggestion,
                key=f"suggestion-{SUGGESTED_QUESTIONS.index(suggestion)}",
                use_container_width=True,
                on_click=use_suggested_question,
                args=(suggestion,),
            )

input_value = st.session_state.pop("pending_question", None)
question = st.chat_input(
    "Ask anything about this repository…",
    disabled=not connected,
)
question = question or input_value
if question:
    api_key = get_openrouter_api_key()
    if not api_key:
        st.error("Add OPENROUTER_API_KEY to your local .env file, then restart the app.")
    else:
        prior_history = [
            ChatMessage(role=message["role"], content=message["content"])
            for message in st.session_state.messages
            if message.get("role") in {"user", "assistant"}
        ][-12:]
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Reading the repository and preparing an answer…"):
                try:
                    full_name, answer = asyncio.run(
                        answer_repository_question(
                            st.session_state.repository_url,
                            question,
                            prior_history,
                            api_key,
                        )
                    )
                except HTTPException as error:
                    st.error(error.detail)
                else:
                    st.session_state.repository_name = full_name
                    st.markdown(answer)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer}
                    )

if connected:
    _, clear_column = st.columns([5, 1])
    with clear_column:
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

st.markdown(
    '<div class="chat-footnote">AI can make mistakes. Check important details in the source. &nbsp; · &nbsp; Built with Python.</div>',
    unsafe_allow_html=True,
)
