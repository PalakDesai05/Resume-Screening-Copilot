# 🧭 Resume Screening Copilot (Agentic AI + GenAI)

AI assistant that **reads, scores and ranks resumes against a job description, with clear reasons for every decision.**

## UI
Copilot-style chat home: proactive summary, streamed answers, inline result cards/charts, follow-up suggestion chips, conversation memory (say 'draft an email for him'), and a Dashboard tab.

## Features (maps to the solution slide)
| Capability | Where |
|---|---|
| Automatic resume parsing (PDF / DOCX / TXT) | `copilot/parser.py` |
| Skill & experience matching with the JD | `copilot/skills.py`, `copilot/scorer.py` |
| Match score + ranked shortlist (CSV export) | Shortlist tab |
| Explainable reasons + skill-gap summary | Candidate detail & Skill gaps tabs |
| Bias-aware screening (anonymised profiles) | Toggle in sidebar – name, email, phone, links, gendered words are masked before scoring |
| **Agentic copilot** | `copilot/agent.py` – Claude tool-use loop over 6 tools (`shortlist`, `get_candidate`, `compare`, `find_by_skill`, `skill_gap_summary`, `draft_email`) |

## Run
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python make_samples.py                               # (optional) regenerate sample JD + resumes
streamlit run app.py
```
Open http://localhost:8501 → click **Screen candidates** (sample data is preloaded).

### Enable the GenAI agent
Set `ANTHROPIC_API_KEY` (env var or paste in sidebar). Optional `COPILOT_MODEL` (default `claude-sonnet-5-5`).
Without a key the copilot still works using an offline rule-based agent calling the same tools.

## How scoring works (transparent, no black box)
`Score = 55% skills (required ×2, preferred ×1) + 20% semantic TF‑IDF similarity + 25% experience` – weights adjustable in the sidebar.
Verdict: ≥70 Strong, ≥50 Potential, else Weak.

## Copilot prompts to try
`top 3` · `why C2?` · `compare C1 and C3` · `skill gaps` · `who knows Docker` · `draft invite for C1` — or free-form with an API key.

## Responsible AI
Anonymised mode on by default; only job-relevant evidence is scored; humans make the final decision. Skill taxonomy is in `copilot/skills.py` — extend it for your domain.
