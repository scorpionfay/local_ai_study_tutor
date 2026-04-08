# agent.py — tutor brain with RAG retrieval + learner memory

import json
import os
import re
import threading
from datetime import datetime
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_classic.chains import RetrievalQA

PROFILE_PATH = "learner_profile.json"
MEMORY_COLLECTION = "tutor_memory"

TUTOR_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a patient and encouraging tutor. You only teach based on the course materials provided below.

IMPORTANT: Always respond in Chinese (中文) by default, regardless of the language of the question. Only switch to another language if the student explicitly asks you to.

Guidelines:
- If the student seems confused, ask one clarifying question before answering fully
- If the student makes a factual error, gently correct it and explain why
- After answering, suggest one related topic from the materials they should review next
- If the answer is not in the course materials, say so honestly — do not make things up
- Keep your tone warm, clear, and encouraging

Course material context:
{context}

Student question (includes learner profile and relevant past sessions):
{question}

Tutor response:"""
)

# ── Profile ───────────────────────────────────────────────────────────────────

def load_profile():
    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, "r") as f:
            return json.load(f)
    return {
        "weak_topics": [],
        "strong_topics": [],
        "session_count": 0,
        "notes": ""
    }

def save_profile(profile: dict):
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)

def reset_profile():
    profile = {
        "weak_topics": [],
        "strong_topics": [],
        "session_count": 0,
        "notes": ""
    }
    save_profile(profile)
    return profile

def format_profile(profile: dict) -> str:
    weak   = ", ".join(profile["weak_topics"])  or "none identified yet"
    strong = ", ".join(profile["strong_topics"]) or "none identified yet"
    notes  = profile.get("notes", "").strip()    or "none"
    return (
        f"Sessions completed: {profile['session_count']}. "
        f"Topics the student struggles with: {weak}. "
        f"Topics the student knows well: {strong}. "
        f"Student notes: {notes}."
    )

# ── Auto profile update ───────────────────────────────────────────────────────

def auto_update_profile(question: str, answer: str, profile: dict, llm) -> dict:
    """Use LLM to detect topic mastery/confusion and silently update profile."""
    prompt = (
        "Analyze this tutoring exchange. Did the student show confusion about a specific topic, "
        "or clearly demonstrate understanding of one?\n\n"
        f"Student: {question}\nTutor: {answer}\n\n"
        "Respond with JSON only, no explanation:\n"
        '{"new_weak": ["topic if confused"], "new_strong": ["topic if understood"]}\n'
        "Use empty lists if nothing is clear. Keep topics short (2-4 words).\nJSON:"
    )
    try:
        raw = llm.invoke(prompt)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return profile
        data = json.loads(match.group())
        changed = False
        for topic in data.get("new_weak", []):
            if topic and topic not in profile["weak_topics"]:
                profile["weak_topics"].append(topic)
                changed = True
        for topic in data.get("new_strong", []):
            if topic and topic not in profile["strong_topics"]:
                profile["strong_topics"].append(topic)
                changed = True
        if changed:
            save_profile(profile)
    except Exception:
        pass
    return profile

def async_update_profile(question: str, answer: str, profile: dict, llm):
    """Run auto_update_profile in a background thread (non-blocking)."""
    t = threading.Thread(
        target=auto_update_profile,
        args=(question, answer, profile, llm),
        daemon=True
    )
    t.start()

# ── Long-term memory ──────────────────────────────────────────────────────────

def retrieve_memories(question: str, embeddings, k: int = 2) -> str:
    """Retrieve relevant past session summaries from ChromaDB."""
    try:
        mem_db = Chroma(
            persist_directory="./db",
            embedding_function=embeddings,
            collection_name=MEMORY_COLLECTION
        )
        results = mem_db.similarity_search(question, k=k)
        if not results:
            return ""
        return "\n".join(f"- {r.page_content}" for r in results)
    except Exception:
        return ""

def save_session_memory(summary: str, embeddings):
    """Persist a session summary to the memory collection in ChromaDB."""
    try:
        mem_db = Chroma(
            persist_directory="./db",
            embedding_function=embeddings,
            collection_name=MEMORY_COLLECTION
        )
        mem_db.add_documents([Document(
            page_content=summary,
            metadata={"type": "session_summary", "date": datetime.now().isoformat()}
        )])
    except Exception:
        pass

def generate_session_summary(messages: list, llm) -> str:
    """Summarise the last session for long-term memory storage."""
    user_messages = [m for m in messages if m["role"] == "user"]
    if len(user_messages) < 2:
        return ""
    convo = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in messages[-12:]
    )
    prompt = (
        "Summarise this tutoring session in 2-3 sentences. "
        "Focus on: topics covered, what the student understood well, and what they struggled with.\n\n"
        f"{convo}\n\nSummary:"
    )
    try:
        return llm.invoke(prompt).strip()
    except Exception:
        return ""

def async_save_memory(messages: list, embeddings, llm):
    """Generate and save session memory in a background thread."""
    def _run():
        summary = generate_session_summary(messages, llm)
        if summary:
            save_session_memory(summary, embeddings)
    threading.Thread(target=_run, daemon=True).start()

# ── Chain ─────────────────────────────────────────────────────────────────────

def build_chain():
    embeddings = OllamaEmbeddings(model="shaw/dmeta-embedding-zh")
    db = Chroma(
        persist_directory="./db",
        embedding_function=embeddings
    )
    retriever = db.as_retriever(search_kwargs={"k": 4})
    llm = OllamaLLM(model="gemma4:e4b", temperature=0.3)
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": TUTOR_PROMPT},
        return_source_documents=True
    )
    return chain, embeddings, llm

def ask_tutor(question: str, profile: dict, chain, embeddings) -> str:
    profile_text = format_profile(profile)
    memories = retrieve_memories(question, embeddings)

    enriched = f"[Learner profile: {profile_text}]"
    if memories:
        enriched += f"\n[Relevant past sessions:\n{memories}]"
    enriched += f"\n\nQuestion: {question}"

    result = chain.invoke({"query": enriched})
    return result["result"]
