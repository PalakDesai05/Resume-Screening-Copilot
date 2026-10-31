# 🧭 Resume Screening Copilot

An agentic AI + GenAI assistant that **reads, scores and ranks resumes** against a job description, with a clear reason for every decision.
Academic project for AAILLM (B.Tech IT, A.Y. 2026-27), Sanjivani College of Engineering, Kopargaon.

## Quick start

```bash
# Windows: double-click run.bat      macOS/Linux: ./run.sh
# or manually:
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Open http://localhost:8501, keep **Bundled sample resumes** selected and press **Screen resumes**.

**GenAI mode (optional):** paste an Anthropic API key in the sidebar (or set `ANTHROPIC_API_KEY`, see `.env.example`).
Without a key the copilot uses the **offline rule-based agent**, which calls the very same 8 tools, so the demo always works.

## Features
| Feature | Where |
|---|---|
| Parse PDF / DOCX / TXT, extract ~70 skills + years of experience | `engine.py` |
| Weighted score out of 100: **55% skills** (required count double) · **20% semantic** (TF-IDF cosine) · **25% experience** | `engine.score_all` |
| Verdict: 70+ Strong · 50-69 Potential · <50 Weak. No auto-rejection | `engine.verdict` |
| Bias-aware mode: masks name, email, phone, links, he/she; candidates shown as C1, C2…; identity revealed on shortlisting | `engine.anonymise`, UI |
| Explainable results: matched / missing skills, score breakdown, adjustable weights | `app.py` |
| Agentic copilot with 8 tools: `shortlist, recommend, get_candidate, compare, find_by_skill, skill_gap_summary, interview_questions, draft_email` | `agent.py` |
| CSV export of ranking and shortlist | `app.py` |

## Project structure
```
app.py            Streamlit UI (styling, tabs, chat)
engine.py         parser · skills · experience · anonymiser · scorer
agent.py          8 tools · offline agent · Claude tool-use loop
sample_data/      5 fictional resumes + job description
.streamlit/       theme config
```

## Using your own data
Choose **Upload my own**, add resumes, and edit the job description. For best results put skills under
`Required skills` and `Preferred skills` headings and state the experience bar like `3+ years`.
Add skills by editing the `_RAW` dictionary at the top of `engine.py`.

## Try these in the copilot
*Who should I interview first?* · *Compare C1 and C5* · *Who has Docker?* · *Skill gaps in the pool* · *Interview questions for C1* · *Draft an invite for him*

## Limitations
Limited skill dictionary · scanned PDFs need OCR · experience is estimated from dates and phrases · semantic part is TF-IDF (not neural embeddings).
Academic prototype, **not a certified hiring tool** - the recruiter always makes the final decision. Resumes are processed in the session only; nothing is stored.

## Future scope
OCR for scanned resumes · sentence-transformer embeddings · larger skill taxonomy and more languages · recruiter login + database · ATS integration and bias audits.
