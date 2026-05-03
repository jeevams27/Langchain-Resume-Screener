# 📄 ATS Resume Screener

A smart resume screening tool built with **LangChain + Groq + pdfplumber + Streamlit** that gives you two scores:

- 🔢 **ATS Score** — keyword match score (how real ATS systems like Naukri/Workday filter you)
- 🤖 **AI Score** — contextual analysis using Llama 3.1 via Groq (understands your projects and experience)

Upload your resume PDF, paste any job description, and get instant feedback on matched skills, missing keywords, strengths, and improvement tips.

---

## 🖥️ Demo

> Paste JD + Upload Resume → Get ATS Score + AI Analysis + Improvement Tips instantly

---

## 🏗️ Project Structure

```
resume-screener/
├── extractor.py      ← pdfplumber: reads PDF, extracts + cleans text
├── screener.py       ← LangChain + Groq: ATS keyword scoring + AI analysis
├── app.py            ← Streamlit: file upload UI + displays results
├── requirements.txt
└── .env.example
```

Each file has one job — separation of concerns.

---

## ⚙️ Tech Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| PDF reading | pdfplumber | Extract text from uploaded resume PDF |
| AI framework | LangChain (LCEL) | `prompt \| llm \| parser` pipeline |
| LLM | Groq — Llama 3.1 | Free, fast AI analysis |
| Output schema | Pydantic | Structured JSON output from AI |
| UI | Streamlit | Web interface, file uploader |

---

## 🧠 How It Works

```
User uploads PDF + pastes JD
           │
           ▼
    extractor.py
    pdfplumber reads every page
    cleans text with regex
           │
           ▼
    screener.py — Part 1 (no API)
    ATS score = keyword set intersection
    matched = jd_keywords & resume_keywords
    missing = jd_keywords - resume_keywords
           │
           ▼
    screener.py — Part 2 (1 API call)
    LangChain chain:
    prompt | llm | parser
    → structured JSON via Pydantic
           │
           ▼
    app.py displays
    ATS score + AI score + chips + tips
```

---

## 🚀 Run Locally

```bash
# 1. Clone
git clone https://github.com/yourusername/langchain-resume-screener
cd langchain-resume-screener

# 2. Install
pip install -r requirements.txt

# 3. Add your Groq API key (free at console.groq.com)
echo "GROQ_API_KEY=your_key_here" > .env

# 4. Run
streamlit run app.py
```

---

## 🌐 Run on Google Colab (Free)

```python
!pip install langchain-core langchain-groq langchain streamlit pdfplumber pydantic -q
!npm install -g localtunnel -q

import os, subprocess, time
os.environ["GROQ_API_KEY"] = "your_key_here"

subprocess.Popen(["streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"])
time.sleep(5)

!npx localtunnel --port 8501
```

---

## 📦 Requirements

```
langchain-core
langchain-groq
langchain
streamlit
pdfplumber
pydantic
python-dotenv
```

---

## 💡 Key Concepts Learned

- **Separation of concerns** — 3 files, each with one job
- **LangChain LCEL** — `prompt | llm | parser` pipeline
- **Pydantic schemas** — structured, validated AI output
- **Python sets** — `&` intersection and `-` difference for keyword matching
- **pdfplumber** — multi-page PDF text extraction and cleaning
- **Streamlit** — `@st.cache_resource`, `file_uploader`, `st.progress()`
- **Environment variables** — never hardcode API keys

---
*Built to learn LangChain — and to solve a real problem I face every day as a fresher job hunter.*
