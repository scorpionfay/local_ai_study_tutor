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
    page_title="AI 学习助教",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 我的 AI 学习助教")
st.caption("基于 gemma4:e4b · RAG 检索 · 你的课程材料")

# ── Session state init ────────────────────────────────────────────────────────
if "profile" not in st.session_state:
    st.session_state.profile = load_profile()
    st.session_state.profile["session_count"] += 1
    save_profile(st.session_state.profile)

if "chain" not in st.session_state:
    with st.spinner("⏳ 正在加载课程材料..."):
        chain, embeddings, llm = build_chain()
        st.session_state.chain = chain
        st.session_state.embeddings = embeddings
        st.session_state.llm = llm

if "session_id" not in st.session_state:
    st.session_state.session_id = create_session()
    welcome = (
        "你好！我是你的专属学习助教。你可以问我任何课程材料里的问题，"
        "我会帮你深入理解。今天想学什么？"
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
    if st.button("➕ 新对话", use_container_width=True, type="primary"):
        # Save memory of the current session before starting a new one
        async_save_memory(
            st.session_state.messages,
            st.session_state.embeddings,
            st.session_state.llm
        )
        st.session_state.session_id = create_session()
        welcome = "新对话已开始！今天想学什么？"
        st.session_state.messages = [{
            "role": "assistant",
            "content": welcome,
            "timestamp": datetime.now().isoformat()
        }]
        save_message(st.session_state.session_id, "assistant", welcome)
        st.rerun()

    st.divider()

    # ── Past sessions ─────────────────────────────────────────────────────────
    st.subheader("🕘 历史对话")
    sessions = list_sessions()

    if not sessions:
        st.caption("还没有历史对话")
    else:
        for s in sessions:
            date_str = s["created_at"][:16].replace("T", " ")
            is_active = s["id"] == st.session_state.session_id
            label = f"{'▶ ' if is_active else ''}对话 {s['id']}  •  {s['msg_count']} 条消息\n{date_str}"
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
    st.subheader("📊 学习档案")
    profile = st.session_state.profile
    st.write(f"**已完成学习次数：** {profile['session_count']}")

    st.divider()

    # Weak topics
    st.write("**🔴 薄弱知识点：**")
    weak_to_remove = None
    if not profile["weak_topics"]:
        st.caption("_暂未标记_")
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
        "添加薄弱知识点...",
        key="new_weak_input",
        label_visibility="collapsed",
        placeholder="添加薄弱知识点..."
    )
    if st.button("➕ 添加", key="add_weak") and new_weak.strip():
        if new_weak.strip() not in profile["weak_topics"]:
            profile["weak_topics"].append(new_weak.strip())
            save_profile(profile)
            st.rerun()

    st.divider()

    # Strong topics
    st.write("**🟢 掌握良好：**")
    strong_to_remove = None
    if not profile["strong_topics"]:
        st.caption("_暂未标记_")
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
        "添加掌握良好的知识点...",
        key="new_strong_input",
        label_visibility="collapsed",
        placeholder="添加掌握良好的知识点..."
    )
    if st.button("➕ 添加", key="add_strong") and new_strong.strip():
        if new_strong.strip() not in profile["strong_topics"]:
            profile["strong_topics"].append(new_strong.strip())
            save_profile(profile)
            st.rerun()

    st.divider()

    # Notes
    st.write("**📝 个人笔记：**")
    notes = st.text_area(
        "笔记",
        value=profile.get("notes", ""),
        height=120,
        key="notes_input",
        label_visibility="collapsed",
        placeholder="写下任何你想记住的内容..."
    )
    if st.button("💾 保存笔记", use_container_width=True):
        profile["notes"] = notes
        save_profile(profile)
        st.success("笔记已保存！")

    st.divider()

    # Reset
    st.write("**⚠️ 危险操作：**")
    if not st.session_state.confirm_reset:
        if st.button("🔄 重置学习档案", use_container_width=True):
            st.session_state.confirm_reset = True
            st.rerun()
    else:
        st.warning("这将清除所有知识点标记、笔记和学习次数，确定吗？")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 确认重置", use_container_width=True):
                st.session_state.profile = reset_profile()
                st.session_state.confirm_reset = False
                st.success("档案已重置！")
                st.rerun()
        with col2:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()

# ── Main chat area ────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "timestamp" in msg:
            st.caption(msg["timestamp"][:16].replace("T", " "))

# Chat input
if question := st.chat_input("问助教任何问题..."):
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
        with st.spinner("思考中..."):
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
