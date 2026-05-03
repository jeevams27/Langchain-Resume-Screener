# 🧠 LifeBot — Personal AI Advisor with Long-Term Memory

A Streamlit chatbot powered by Groq LLaMA 3.3 that **remembers you across sessions**.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How memory works

| Type | What it stores | How long |
|------|---------------|----------|
| Short-term | Last 20 messages | Current session only |
| Long-term (facts) | Personal details, goals, problems extracted by AI | Forever (in JSON file) |
| Long-term (sessions) | 2-3 sentence summary of each session | Forever (in JSON file) |
| Problem tags | Life topic categories | Forever |

## Memory storage

Memories are saved to `user_memories/<username>.json` — one file per user.

```json
{
  "username": "Jeeva",
  "created_at": "2025-01-01T10:00:00",
  "key_facts": [
    "Looking for a Data Analyst job in Chennai",
    "Has a project on LangChain Resume Screener"
  ],
  "problem_tags": ["job search", "career"],
  "sessions": [
    {
      "date": "2025-01-01 10:00",
      "summary": "User discussed job search strategy..."
    }
  ]
}
```

## Features

- Multi-user support (each user gets their own memory file)
- Session summarization via AI (auto-extracts key info)
- Fact extraction (AI pulls personal details from conversation)
- Topic tagging (job search, finance, health, etc.)
- Memory injected into system prompt at start of each session

## Get Groq API Key

Free at [console.groq.com](https://console.groq.com) — no credit card needed.
