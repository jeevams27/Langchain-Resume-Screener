# ============================================================
#   screener.py
#   Job : ATS keyword scoring + LangChain AI analysis
#   Used by : app.py
# ============================================================

import os
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field


# ─── Output Schema ──────────────────────────────────────────
class ResumeAnalysis(BaseModel):
    ai_score: int = Field(description="AI-judged overall fit score 0–100")
    matched_skills: list = Field(description="Skills found in both JD and resume")
    missing_skills: list = Field(description="Skills in JD but missing from resume")
    strengths: list = Field(description="Top 3 strengths of the candidate")
    recommendation: str = Field(description="One of: Strong Fit / Moderate Fit / Weak Fit")
    summary: str = Field(description="2-3 sentence overall analysis")
    improvement_tips: list = Field(description="3 specific tips to improve the resume for this JD")


# ─── ATS Score (Keyword Matching) ───────────────────────────
def calculate_ats_score(jd_text: str, resume_text: str) -> dict:
    """
    Pure keyword-based ATS scoring — no AI needed.
    Simulates how real ATS systems (Naukri, Workday) filter resumes.

    Returns:
    {
        "ats_score": 72,
        "matched_keywords": ["python", "sql", "power bi"],
        "missing_keywords": ["tableau", "spark"],
        "total_keywords": 10
    }
    """
    # Extract meaningful keywords from JD (skip stop words)
    stop_words = {
        "and", "or", "the", "a", "an", "in", "on", "at", "to", "for",
        "of", "with", "is", "are", "be", "will", "must", "should",
        "experience", "required", "preferred", "ability", "strong",
        "good", "excellent", "knowledge", "understanding", "working",
        "role", "team", "candidate", "position", "job", "skills", "using"
    }

    def extract_keywords(text: str) -> set:
        # Lowercase, split on non-alphanumeric, filter short/stopwords
        words = re.findall(r'[a-zA-Z][a-zA-Z0-9+#\.]*', text.lower())
        return {w for w in words if len(w) > 2 and w not in stop_words}

    jd_keywords      = extract_keywords(jd_text)
    resume_keywords  = extract_keywords(resume_text)

    matched  = jd_keywords & resume_keywords
    missing  = jd_keywords - resume_keywords

    # Score = matched / total jd keywords * 100
    total    = len(jd_keywords)
    score    = round((len(matched) / total) * 100) if total > 0 else 0

    # Return top keywords only (sorted, max 15 each)
    return {
        "ats_score":        min(score, 100),
        "matched_keywords": sorted(list(matched))[:15],
        "missing_keywords": sorted(list(missing))[:15],
        "total_jd_keywords": total
    }


# ─── LangChain AI Analysis ──────────────────────────────────
def get_chain():
    llm = ChatGroq(
        model="llama3-8b-8192",
        temperature=0,
        api_key=os.environ["GROQ_API_KEY"]
    )
    parser = JsonOutputParser(pydantic_object=ResumeAnalysis)
    prompt = ChatPromptTemplate.from_template(
        "You are a senior technical recruiter and ATS specialist.\n"
        "Analyze the resume against the job description carefully.\n"
        "Be honest, specific, and helpful.\n\n"
        "JOB DESCRIPTION:\n{job_description}\n\n"
        "CANDIDATE RESUME:\n{resume}\n\n"
        "{format_instructions}"
    )
    return prompt | llm | parser, parser


def run_full_analysis(jd_text: str, resume_text: str) -> dict:
    """
    Runs both ATS keyword scoring and AI analysis.
    Returns a combined result dict.
    """
    # Step 1: ATS keyword score (fast, no API call)
    ats_result = calculate_ats_score(jd_text, resume_text)

    # Step 2: AI deep analysis (LangChain + Groq)
    chain, parser = get_chain()
    ai_result = chain.invoke({
        "job_description": jd_text,
        "resume":          resume_text,
        "format_instructions": parser.get_format_instructions()
    })

    # Step 3: Merge both results
    return {**ats_result, **ai_result}


# ─── Quick test ─────────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    jd = """
    Role: Data Analyst
    Requirements: Python, SQL, Power BI, Excel, pandas, data visualization,
    ETL pipelines, KPI dashboards, communication skills
    """

    resume = """
    Jeeva R | B.Tech AI & Data Science 2025
    Skills: Python, SQL, Power BI, Excel, pandas, numpy, scikit-learn
    Projects: Uber KPI Dashboard, Retail ETL Pipeline, Customer Segmentation
    Internship: Data Analyst at Innomatics Research Labs (6 months)
    """

    result = run_full_analysis(jd, resume)
    print(f"ATS Score  : {result['ats_score']}/100")
    print(f"AI Score   : {result['ai_score']}/100")
    print(f"Verdict    : {result['recommendation']}")
    print(f"Matched    : {result['matched_keywords']}")
    print(f"Missing    : {result['missing_keywords']}")
    print(f"Tips       : {result['improvement_tips']}")
