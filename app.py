# app.py — full Streamlit UI with chat history, learner profile editing, and reset

import streamlit as st
from datetime import datetime
from agent import (
    load_profile, save_profile, reset_profile,
    build_chain, ask_tutor,
    async_update_profile, async_save_memory
)
from database import (
    init_db, create_session, save_message,
    load_session, list_sessions, delete_session
)

# ── App init ─────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(
    page_title="My AI Tutor",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 My Personal AI Tutor")
st.caption("Powered by gemma4:e4b · RAG · your course materials")

# ── Session state init ────────────────────────────────────────────────────────
if "profile" not in st.session_state:
    st.session_state.profile = load_profile()
    st.session_state.profile["session_count"] += 1
    save_profile(st.session_state.profile)

if "chain" not in st.session_state:
    with st.spinner("⏳ Loading your course materials..."):
        chain, embeddings, llm = build_chain()
        st.session_state.chain = chain
        st.session_state.embeddings = embeddings
        st.session_state.llm = llm

if "session_id" not in st.session_state:
    st.session_state.session_id = create_session()
    welcome = (
        "Hi! I'm your personal tutor. Ask me anything from your course "
        "materials and I'll help you understand it deeply. "
        "What would you like to learn today?"
    )
    st.session_state.messages = [{
        "role": "assistant",
        "content": welcome,
        "timestamp": datetime.now().isoformat()
    }]
    save_message(st.session_state.session_id, "assistant", welcome)

if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:

    # New chat
    if st.button("➕ New chat", use_container_width=True, type="primary"):
        # Save memory of the current session before starting a new one
        async_save_memory(
            st.session_state.messages,
            st.session_state.embeddings,
            st.session_state.llm
        )
        st.session_state.session_id = create_session()
        welcome = "New session started! What would you like to study today?"
        st.session_state.messages = [{
            "role": "assistant",
            "content": welcome,
            "timestamp": datetime.now().isoformat()
        }]
        save_message(st.session_state.session_id, "assistant", welcome)
        st.rerun()

    st.divider()

    # ── Past sessions ─────────────────────────────────────────────────────────
    st.subheader("🕘 Past sessions")
    sessions = list_sessions()

    if not sessions:
        st.caption("No past sessions yet.")
    else:
        for s in sessions:
            date_str = s["created_at"][:16].replace("T", " ")
            is_active = s["id"] == st.session_state.session_id
            label = f"{'▶ ' if is_active else ''}Session {s['id']}  •  {s['msg_count']} msgs\n{date_str}"
            col1, col2 = st.columns([5, 1])
            with col1:
                if st.button(label, key=f"sess_{s['id']}", use_container_width=True):
                    st.session_state.session_id = s["id"]
                    st.session_state.messages = load_session(s["id"])
                    st.rerun()
            with col2:
                if st.button("🗑", key=f"del_{s['id']}"):
                    delete_session(s["id"])
                    if st.session_state.session_id == s["id"]:
                        st.session_state.session_id = create_session()
                        st.session_state.messages = []
                    st.rerun()

    st.divider()

    # ── Learner profile ───────────────────────────────────────────────────────
    st.subheader("📊 Learner profile")
    profile = st.session_state.profile
    st.write(f"**Sessions completed:** {profile['session_count']}")

    st.divider()

    # Weak topics
    st.write("**🔴 Struggling with:**")
    weak_to_remove = None
    if not profile["weak_topics"]:
        st.caption("_Nothing flagged yet_")
    for i, t in enumerate(profile["weak_topics"]):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(f"- {t}")
        with col2:
            if st.button("✕", key=f"rm_weak_{i}"):
                weak_to_remove = t
    if weak_to_remove:
        profile["weak_topics"].remove(weak_to_remove)
        save_profile(profile)
        st.rerun()

    new_weak = st.text_input(
        "Add topic I struggle with...",
        key="new_weak_input",
        label_visibility="collapsed",
        placeholder="Add topic I struggle with..."
    )
    if st.button("➕ Add", key="add_weak") and new_weak.strip():
        if new_weak.strip() not in profile["weak_topics"]:
            profile["weak_topics"].append(new_weak.strip())
            save_profile(profile)
            st.rerun()

    st.divider()

    # Strong topics
    st.write("**🟢 Strong areas:**")
    strong_to_remove = None
    if not profile["strong_topics"]:
        st.caption("_Nothing flagged yet_")
    for i, t in enumerate(profile["strong_topics"]):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(f"- {t}")
        with col2:
            if st.button("✕", key=f"rm_strong_{i}"):
                strong_to_remove = t
    if strong_to_remove:
        profile["strong_topics"].remove(strong_to_remove)
        save_profile(profile)
        st.rerun()

    new_strong = st.text_input(
        "Add topic I know well...",
        key="new_strong_input",
        label_visibility="collapsed",
        placeholder="Add topic I know well..."
    )
    if st.button("➕ Add", key="add_strong") and new_strong.strip():
        if new_strong.strip() not in profile["strong_topics"]:
            profile["strong_topics"].append(new_strong.strip())
            save_profile(profile)
            st.rerun()

    st.divider()

    # Notes
    st.write("**📝 Personal notes:**")
    notes = st.text_area(
        "notes",
        value=profile.get("notes", ""),
        height=120,
        key="notes_input",
        label_visibility="collapsed",
        placeholder="Write anything you want to remember..."
    )
    if st.button("💾 Save notes", use_container_width=True):
        profile["notes"] = notes
        save_profile(profile)
        st.success("Notes saved!")

    st.divider()

    # Reset
    st.write("**⚠️ Danger zone:**")
    if not st.session_state.confirm_reset:
        if st.button("🔄 Reset profile", use_container_width=True):
            st.session_state.confirm_reset = True
            st.rerun()
    else:
        st.warning("This clears all topics, notes and resets your session count. Are you sure?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, reset", use_container_width=True):
                st.session_state.profile = reset_profile()
                st.session_state.confirm_reset = False
                st.success("Profile reset!")
                st.rerun()
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()

# ── Main chat area ────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "timestamp" in msg:
            st.caption(msg["timestamp"][:16].replace("T", " "))

# Chat input
if question := st.chat_input("Ask your tutor anything..."):
    # Show and save user message
    st.session_state.messages.append({
        "role": "user",
        "content": question,
        "timestamp": datetime.now().isoformat()
    })
    save_message(st.session_state.session_id, "user", question)
    with st.chat_message("user"):
        st.write(question)

    # Get tutor answer
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = ask_tutor(
                question,
                st.session_state.profile,
                st.session_state.chain,
                st.session_state.embeddings
            )
        st.write(answer)

    # Save assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "timestamp": datetime.now().isoformat()
    })
    save_message(st.session_state.session_id, "assistant", answer)

    # Auto-update learner profile in background (non-blocking)
    async_update_profile(
        question,
        answer,
        st.session_state.profile,
        st.session_state.llm
    )
