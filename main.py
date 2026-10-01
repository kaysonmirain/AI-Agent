from __future__ import annotations

from pathlib import Path

import ollama
import streamlit as st

from ai_agent import AgentSession


st.set_page_config(page_title="AI Agent", page_icon="🤖")
st.title("🤖 AI Agent")

st.caption("A local Ollama assistant that can chat, preview file changes, and work inside one guarded workspace.")

with st.sidebar:
    st.header("Agent settings")
    workspace = st.text_input("Workspace", value=str(Path("agent_workspace").resolve()))
    model = st.text_input("Ollama model", value="qwen2.5-coder:7b")
    apply_changes = st.toggle("Apply file changes", value=False)
    st.caption("Keep this off when you only want a diff preview.")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hi, I am AI Agent. I can answer normally, or you can ask me to create, "
                "append, replace, or delete files inside the selected workspace."
            ),
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def looks_like_file_task(prompt: str) -> bool:
    lowered = prompt.lower()
    actions = ["create ", "write ", "append ", "replace ", "delete "]
    return any(action in lowered for action in actions)


def stream_model_response(prompt: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are AI Agent, the agent version of Kayson's AI Chatbot project. "
                "Be concise, practical, and explain file actions before they happen."
            ),
        },
        *st.session_state.messages[-8:],
        {"role": "user", "content": prompt},
    ]
    response = ""
    stream = ollama.chat(model=model, messages=messages, stream=True)
    placeholder = st.empty()
    for chunk in stream:
        response += chunk["message"]["content"]
        placeholder.markdown(response)
    return response


if prompt := st.chat_input("Ask AI Agent something, or give it a workspace task..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response = stream_model_response(prompt)
            if looks_like_file_task(prompt):
                st.divider()
                session = AgentSession(workspace)
                record = session.run_task(prompt, apply=apply_changes)
                for change in record.changes:
                    action = "Applied" if record.applied else "Previewed"
                    st.markdown(f"**{action} `{change['action']}` on `{change['path']}`**")
                    st.code(change["diff"] or "(no text diff)", language="diff")
                st.caption("Audit log saved under `.agent/runs/` in the selected workspace.")
        except Exception as exc:
            response = f"Something went wrong: {exc}"
            st.error(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
