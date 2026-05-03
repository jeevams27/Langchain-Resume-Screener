# ============================================================
#   app.py
#   Job : Streamlit frontend — file upload, display results
#   Imports from : extractor.py, screener.py
# ============================================================

import streamlit as st
import os

# Our own modules
from extractor import extract_text_from_pdf, extract_sections
from screener import run_full_analysis

# ─── Page Config ────────────────────────────────────────────
st.set_page_config(
    page_title="ATS Resume Screener",
    page_icon="📄",
    layout="wide"
)

# ─── Styling ────────────────────────────────────────────────
st.markdown("""
<style>
    .skill-chip {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.82rem;
        margin: 3px;
        font-weight: 500;
    }
    .matched  { background: #dcfce7; color: #166534; }
    .missing  { background: #fee2e2; color: #991b1b; }
    .strength { background: #dbeafe; color: #1e40af; }
    .tip      { background: #fef9c3; color: #854d0e; }
    .section-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ─── Helpers ────────────────────────────────────────────────
def score_color(score: int):
    if score >= 75:
        return "#166534", "#dcfce7"
    elif score >= 50:
        return "#92400e", "#fef9c3"
    else:
        return "#991b1b", "#fee2e2"

def verdict_emoji(rec: str):
    return {"Strong Fit": "🟢", "Moderate Fit": "🟡", "Weak Fit": "🔴"}.get(rec, "⚪")

def metric_card(value, label, text_color, bg_color):
    return f"""
    <div style="background:{bg_color};border-radius:12px;padding:1rem;text-align:center;">
        <p style="font-size:2rem;font-weight:700;margin:0;color:{text_color};">{value}</p>
        <p style="font-size:0.78rem;color:{text_color};margin:0;opacity:0.85;">{label}</p>
    </div>"""


# ─── Header ─────────────────────────────────────────────────
st.title("📄 ATS Resume Screener")
st.caption("Upload your resume PDF · Paste the Job Description · Get ATS + AI analysis")
st.divider()

# ─── Input Section ──────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Job Description")
    jd_text = st.text_area(
        "JD",
        height=300,
        placeholder="Paste the full job description here...",
        label_visibility="collapsed"
    )

with col2:
    st.subheader("📎 Upload Resume (PDF)")
    uploaded_file = st.file_uploader(
        "Upload Resume",
        type=["pdf"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        st.success(f"✅ {uploaded_file.name} uploaded successfully!")

        # Show extracted text preview
        with st.expander("👁️ Preview extracted text"):
            with st.spinner("Extracting text from PDF..."):
                extracted_resume = extract_text_from_pdf(uploaded_file)
                uploaded_file.seek(0)  # reset file pointer after reading
                st.text_area(
                    "Extracted",
                    value=extracted_resume,
                    height=200,
                    label_visibility="collapsed",
                    disabled=True
                )

                # Show detected sections
                sections = extract_sections(extracted_resume)
                if sections:
                    st.markdown("**Sections detected:** " +
                        " · ".join([f"`{s}`" for s in sections.keys()]))

# ─── Run Button ─────────────────────────────────────────────
st.markdown("")
run = st.button("🔍 Analyze Resume", use_container_width=True, type="primary")

# ─── Results ────────────────────────────────────────────────
if run:
    if not jd_text.strip():
        st.warning("Please paste a Job Description.")
    elif not uploaded_file:
        st.warning("Please upload a resume PDF.")
    else:
        with st.spinner("Running ATS scan + AI analysis..."):
            try:
                # Re-extract text (file pointer was reset above)
                uploaded_file.seek(0)
                resume_text = extract_text_from_pdf(uploaded_file)

                # Run both ATS + AI
                result = run_full_analysis(jd_text, resume_text)

                st.divider()
                st.subheader("📊 Screening Report")

                # ── Score Cards ──────────────────────────────
                ats_tc, ats_bg  = score_color(result["ats_score"])
                ai_tc,  ai_bg   = score_color(result["ai_score"])
                rec_emoji = verdict_emoji(result["recommendation"])
                rec_tc, rec_bg  = score_color(
                    100 if result["recommendation"] == "Strong Fit"
                    else 60 if result["recommendation"] == "Moderate Fit"
                    else 30
                )

                m1, m2, m3, m4 = st.columns(4)
                m1.markdown(metric_card(f"{result['ats_score']}", "ATS Score / 100", ats_tc, ats_bg), unsafe_allow_html=True)
                m2.markdown(metric_card(f"{result['ai_score']}",  "AI Score / 100",  ai_tc,  ai_bg),  unsafe_allow_html=True)
                m3.markdown(metric_card(f"{len(result['matched_keywords'])}", "Keywords Matched", "#1e40af", "#dbeafe"), unsafe_allow_html=True)
                m4.markdown(metric_card(f"{rec_emoji} {result['recommendation']}", "Verdict", rec_tc, rec_bg), unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Score Bars ───────────────────────────────
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown('<p class="section-label">ATS keyword score</p>', unsafe_allow_html=True)
                    st.progress(result["ats_score"] / 100)
                    st.caption(f"{result['ats_score']}% of JD keywords found in your resume")
                with c2:
                    st.markdown('<p class="section-label">AI fit score</p>', unsafe_allow_html=True)
                    st.progress(result["ai_score"] / 100)
                    st.caption("Based on context, experience & project relevance")

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Summary ──────────────────────────────────
                st.info(f"📝 **Summary:** {result['summary']}")

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Keywords & Skills ────────────────────────
                st.subheader("🔑 Keyword Analysis")
                k1, k2 = st.columns(2)

                with k1:
                    st.markdown('<p class="section-label">✅ Matched keywords</p>', unsafe_allow_html=True)
                    if result["matched_keywords"]:
                        st.markdown(
                            " ".join([f'<span class="skill-chip matched">{k}</span>'
                                      for k in result["matched_keywords"]]),
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown("No keyword matches found.")

                with k2:
                    st.markdown('<p class="section-label">❌ Missing keywords</p>', unsafe_allow_html=True)
                    if result["missing_keywords"]:
                        st.markdown(
                            " ".join([f'<span class="skill-chip missing">{k}</span>'
                                      for k in result["missing_keywords"]]),
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown('<span class="skill-chip matched">All keywords present!</span>',
                                    unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── AI Skills + Strengths ────────────────────
                st.subheader("🤖 AI Analysis")
                a1, a2, a3 = st.columns(3)

                with a1:
                    st.markdown('<p class="section-label">✅ Matched skills</p>', unsafe_allow_html=True)
                    st.markdown(
                        " ".join([f'<span class="skill-chip matched">{s}</span>'
                                  for s in result["matched_skills"]]),
                        unsafe_allow_html=True
                    )

                with a2:
                    st.markdown('<p class="section-label">❌ Missing skills</p>', unsafe_allow_html=True)
                    chips = result["missing_skills"]
                    st.markdown(
                        " ".join([f'<span class="skill-chip missing">{s}</span>' for s in chips])
                        if chips else '<span class="skill-chip matched">None!</span>',
                        unsafe_allow_html=True
                    )

                with a3:
                    st.markdown('<p class="section-label">💪 Key strengths</p>', unsafe_allow_html=True)
                    st.markdown(
                        " ".join([f'<span class="skill-chip strength">{s}</span>'
                                  for s in result["strengths"]]),
                        unsafe_allow_html=True
                    )

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Improvement Tips ─────────────────────────
                st.subheader("💡 How to improve your resume for this JD")
                for i, tip in enumerate(result["improvement_tips"], 1):
                    st.markdown(
                        f'<span class="skill-chip tip">💡 {i}. {tip}</span>',
                        unsafe_allow_html=True
                    )

            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.info("Make sure your GROQ_API_KEY is set correctly.")

# ─── Footer ─────────────────────────────────────────────────
st.divider()
st.caption("extractor.py → pdfplumber  |  screener.py → LangChain + Groq  |  app.py → Streamlit")
