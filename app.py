import streamlit as st
import json
import os
from datetime import datetime
from groq import Groq

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
MEMORY_DIR   = "user_memories"
MODEL        = "llama-3.3-70b-versatile"
MAX_HISTORY  = 20   # messages kept in live context
MAX_SESSIONS = 5    # past sessions injected into prompt

st.set_page_config(
    page_title="LifeBot – Your Personal AI Advisor",
    page_icon="🧠",
    layout="centered",
)

# ─────────────────────────────────────────────
#  MEMORY HELPERS
# ─────────────────────────────────────────────
def load_memory(username: str) -> dict:
    os.makedirs(MEMORY_DIR, exist_ok=True)
    path = f"{MEMORY_DIR}/{username.lower().strip()}.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {
        "username":     username,
        "created_at":  datetime.now().isoformat(),
        "key_facts":   [],
        "problem_tags":[],
        "sessions":    [],
    }

def save_memory(username: str, memory: dict):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    path = f"{MEMORY_DIR}/{username.lower().strip()}.json"
    with open(path, "w") as f:
        json.dump(memory, f, indent=2)

def build_memory_context(memory: dict) -> str:
    parts = []
    if memory["key_facts"]:
        parts.append("Key facts about this user:")
        for fact in memory["key_facts"][-15:]:
            parts.append(f"  - {fact}")
    if memory["sessions"]:
        parts.append("\nPrevious session summaries (newest first):")
        for s in reversed(memory["sessions"][-MAX_SESSIONS:]):
            parts.append(f"  [{s['date']}] {s['summary']}")
    if memory["problem_tags"]:
        unique = list(dict.fromkeys(memory["problem_tags"]))[-10:]
        parts.append(f"\nOngoing topics: {', '.join(unique)}")
    return "\n".join(parts)

# ─────────────────────────────────────────────
#  GROQ HELPERS
# ─────────────────────────────────────────────
def call_groq(client: Groq, system: str, messages: list, max_tokens=1024) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}] + messages,
        temperature=0.7,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()

def summarize_session(client: Groq, messages: list):
    if len(messages) < 2:
        return None
    convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    prompt = (
        "Summarize this conversation in 2-3 sentences. Cover:\n"
        "1. The user's main problem(s)\n"
        "2. Key advice given\n"
        "3. Action items or goals mentioned\n\n"
        f"Conversation:\n{convo}\n\nReturn ONLY the summary text."
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()

def extract_facts(client: Groq, messages: list, existing: list) -> list:
    if len(messages) < 2:
        return []
    convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages[-8:])
    known = "\n".join(existing[-10:]) if existing else "None"
    prompt = (
        "Extract 1-3 NEW personal facts about the USER from this conversation.\n"
        "Good facts: goals, ongoing problems, preferences, deadlines, personal context.\n"
        f"Do NOT repeat already known facts:\n{known}\n\n"
        f"Conversation:\n{convo}\n\n"
        'Reply ONLY with a JSON array like ["fact1","fact2"]. If none, return [].'
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )
    try:
        raw = resp.choices[0].message.content.strip().replace("```json","").replace("```","")
        return json.loads(raw)
    except Exception:
        return []

def extract_tags(client: Groq, messages: list) -> list:
    if len(messages) < 2:
        return []
    convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages[-6:])
    prompt = (
        "What 1-3 life topics does this conversation cover?\n"
        "Pick from: job search, finance, health, relationships, study, business, "
        "stress, career, family, productivity, housing, personal growth, other.\n\n"
        f"Conversation:\n{convo}\n\n"
        'Reply ONLY with a JSON array like ["job search","finance"].'
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
    )
    try:
        raw = resp.choices[0].message.content.strip().replace("```json","").replace("```","")
        return json.loads(raw)
    except Exception:
        return []

# ─────────────────────────────────────────────
#  SYSTEM PROMPT BUILDER
# ─────────────────────────────────────────────
def build_system_prompt(username: str, memory_context: str) -> str:
    today = datetime.now().strftime("%A, %d %B %Y")
    prompt = (
        f"You are LifeBot — a personal AI life advisor for {username}. Today is {today}.\n\n"
        f"Your job: Help {username} solve real-life problems with practical, specific, actionable advice.\n\n"
        "Your personality:\n"
        "- Warm but direct. No fluff, no filler.\n"
        "- You have a good memory. You remember what the user told you before.\n"
        "- You follow up naturally on past issues.\n"
        "- You give step-by-step plans, not vague suggestions.\n"
        "- You treat the user as an intelligent adult.\n\n"
    )
    if memory_context:
        prompt += (
            f"=== WHAT YOU REMEMBER ABOUT {username.upper()} ===\n"
            f"{memory_context}\n"
            "==============================================\n\n"
            "Use this memory naturally. Don't dump all facts at once — weave them in when relevant.\n"
            "Reference past sessions and ask for updates when appropriate.\n\n"
        )
    prompt += (
        "Rules:\n"
        "- Ask good clarifying questions to understand the problem fully.\n"
        "- Always end with ONE of: a follow-up question OR a concrete next action step.\n"
        "- If the user says 'I don't know what to do', break the problem into smaller pieces.\n"
        "- Never give generic advice. Make it specific to what you know about this user."
    )
    return prompt

# ─────────────────────────────────────────────
#  END SESSION
# ─────────────────────────────────────────────
def end_session(client: Groq, username: str, memory: dict, messages: list):
    with st.spinner("Saving session memory..."):
        summary   = summarize_session(client, messages)
        new_facts = extract_facts(client, messages, memory["key_facts"])
        new_tags  = extract_tags(client, messages)

        if summary:
            memory["sessions"].append({
                "date":    datetime.now().strftime("%Y-%m-%d %H:%M"),
                "summary": summary,
            })
        if new_facts:
            memory["key_facts"].extend(new_facts)
        if new_tags:
            memory["problem_tags"].extend(new_tags)

        save_memory(username, memory)
    return summary

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.lb-header { text-align:center; padding:1.8rem 0 0.8rem; }
.lb-header h1 {
    font-size:2.2rem; font-weight:600; margin:0;
    background:linear-gradient(135deg,#6ee7f7,#a78bfa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.lb-header p { color:#94a3b8; font-size:0.92rem; margin-top:0.3rem; }

.stats-bar { display:flex; gap:0.6rem; margin:0.8rem 0; flex-wrap:wrap; }
.stat-chip {
    background:#1e293b; border:1px solid #334155;
    border-radius:20px; padding:0.25rem 0.75rem;
    font-size:0.78rem; color:#94a3b8;
}

.chat-user {
    background:#1e3a5f; color:#e2e8f0;
    border-radius:16px 16px 4px 16px;
    padding:0.7rem 1rem; margin:0.35rem 0 0.35rem 3.5rem;
    font-size:0.92rem; line-height:1.65;
}
.chat-bot {
    background:#1e293b; color:#cbd5e1;
    border-radius:16px 16px 16px 4px;
    padding:0.7rem 1rem; margin:0.35rem 3.5rem 0.35rem 0;
    font-size:0.92rem; line-height:1.65;
    border-left:3px solid #6ee7f7;
}
.chat-role { font-size:0.68rem; font-weight:600; text-transform:uppercase; letter-spacing:0.07em; margin-bottom:0.25rem; }
.role-user { color:#60a5fa; }
.role-bot  { color:#6ee7f7; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
for key, default in {
    "logged_in": False,
    "username":  "",
    "messages":  [],
    "memory":    None,
    "client":    None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown('<div class="lb-header"><h1>🧠 LifeBot</h1><p>Your personal AI advisor — that actually remembers you.</p></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        api_key  = st.text_input("🔑 Groq API Key", type="password", placeholder="gsk_...")
        username = st.text_input("👤 Your Name", placeholder="e.g. Jeeva")

        if st.button("Start Chatting →", use_container_width=True, type="primary"):
            if not api_key.strip():
                st.error("Please enter your Groq API key.")
            elif not username.strip():
                st.error("Please enter your name.")
            else:
                try:
                    client = Groq(api_key=api_key.strip())
                    client.chat.completions.create(model=MODEL, messages=[{"role":"user","content":"hi"}], max_tokens=5)
                    st.session_state.client    = client
                    st.session_state.username  = username.strip()
                    st.session_state.memory    = load_memory(username.strip())
                    st.session_state.logged_in = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Connection failed: {e}")

        st.markdown('<div style="text-align:center;margin-top:1rem;color:#475569;font-size:0.8rem;">Free Groq API key → <a href="https://console.groq.com" target="_blank" style="color:#6ee7f7;">console.groq.com</a></div>', unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────
#  MAIN CHAT
# ─────────────────────────────────────────────
username = st.session_state.username
memory   = st.session_state.memory
client   = st.session_state.client
messages = st.session_state.messages

st.markdown(f'<div class="lb-header"><h1>🧠 LifeBot</h1><p>Hey <strong>{username}</strong> — I remember you.</p></div>', unsafe_allow_html=True)

# Stats
sessions_count = len(memory["sessions"])
facts_count    = len(memory["key_facts"])
tags           = list(dict.fromkeys(memory["problem_tags"]))[-4:]
chips = (
    f'<span class="stat-chip">💬 {sessions_count} session{"s" if sessions_count!=1 else ""} saved</span>'
    f'<span class="stat-chip">📌 {facts_count} facts remembered</span>'
    + "".join(f'<span class="stat-chip">🏷️ {t}</span>' for t in tags)
)
st.markdown(f'<div class="stats-bar">{chips}</div>', unsafe_allow_html=True)

# Memory expander
memory_context = build_memory_context(memory)
if memory_context:
    with st.expander("🧠 What I remember about you", expanded=False):
        st.markdown(memory_context)
else:
    st.info("First conversation! I'll start building your memory from today.")

st.divider()

# Opening message
if not messages:
    if memory["sessions"]:
        last   = memory["sessions"][-1]
        opener = (f"Hey {username}! Good to see you again. "
                  f"Last time ({last['date'].split()[0]}), we talked about: {last['summary']} "
                  f"How has that been going?")
    elif memory["key_facts"]:
        opener = f"Hey {username}! Good to see you. What's on your mind today?"
    else:
        opener = (f"Hey {username}! I'm LifeBot — your personal AI advisor. "
                  f"I'll remember everything you share across sessions, so you never have to repeat yourself. "
                  f"What problem are you trying to solve today?")
    messages.append({"role": "assistant", "content": opener})
    st.session_state.messages = messages

# Render messages
for msg in messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-user"><div class="chat-role role-user">You</div>{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-bot"><div class="chat-role role-bot">LifeBot</div>{msg["content"]}</div>', unsafe_allow_html=True)

# Input
user_input = st.chat_input("Type your message here…")
if user_input:
    messages.append({"role": "user", "content": user_input})
    st.session_state.messages = messages
    system = build_system_prompt(username, memory_context)
    with st.spinner("LifeBot is thinking…"):
        reply = call_groq(client, system, messages[-MAX_HISTORY:])
    messages.append({"role": "assistant", "content": reply})
    st.session_state.messages = messages
    st.rerun()

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 👤 {username}")
    st.caption(f"Since: {memory['created_at'][:10]}")
    st.divider()
    st.markdown("**Memory Stats**")
    st.metric("Sessions saved", sessions_count)
    st.metric("Facts learned", facts_count)

    if tags:
        st.markdown("**Your Topics**")
        for t in tags:
            st.markdown(f"• {t}")
    st.divider()

    if st.button("💾 Save & End Session", use_container_width=True, type="primary"):
        if len(messages) > 1:
            summary = end_session(client, username, memory, messages)
            st.session_state.messages = []
            st.session_state.memory   = load_memory(username)
            st.success("Session saved!")
            if summary:
                st.info(f"**Summary:** {summary}")
            st.rerun()
        else:
            st.warning("Have a conversation first!")

    if st.button("🗑️ Clear Chat (don't save)", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username  = ""
        st.session_state.messages  = []
        st.session_state.memory    = None
        st.session_state.client    = None
        st.rerun()

    st.divider()
    st.caption("Memory stored in `user_memories/<name>.json`")
    st.caption("Model: LLaMA 3.3 70B via Groq")
