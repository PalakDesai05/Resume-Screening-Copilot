import os
from html import escape as esc
from pathlib import Path

import pandas as pd
import streamlit as st

import agent as A
import engine as E

st.set_page_config(page_title="Resume Screening Copilot", page_icon="🧭", layout="wide")
SAMPLES = Path(__file__).parent / "sample_data"
COL = {"Strong match": "#15803D", "Potential": "#B45309", "Weak match": "#B91C1C"}
PILL = {"Strong match": "strong", "Potential": "pot", "Weak match": "weak"}

st.markdown("""<style>
:root {
  --teal: #0F766E;
  --teal-hover: #115E59;
  --accent: #EA580C;
  --accent-hover: #C2410C;
  --bg: #F5F5F0;
  --border: #D6D3D1;
  --text: #1C1917;
  --muted: #57534E;
}
html, body, .stApp, [class*="css"] {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  color: var(--text);
}
.stApp { background: var(--bg); }
.block-container { padding-top: 1.2rem; max-width: 1200px; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid var(--border); }

h1, h2, h3, h4, h5, h6 { font-weight: 600 !important; color: var(--text); }

.hero {
  background: var(--teal);
  color: #FFFFFF;
  padding: 1.2rem 1.6rem;
  border-radius: 4px;
  margin-bottom: 1.2rem;
  border: 1px solid var(--teal-hover);
}
.hero .eyebrow {
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.88;
  font-weight: 600;
  margin-bottom: 0.2rem;
}
.hero h1 {
  font-size: 1.8rem !important;
  font-weight: 600 !important;
  margin: 0 0 0.35rem !important;
  color: #FFFFFF !important;
  line-height: 1.2;
  padding: 0;
}
.hero p {
  font-size: 0.95rem;
  opacity: 0.92;
  margin: 0;
  color: #F0FDFA;
}

.card {
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1rem 1.2rem;
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
  margin-bottom: 0.8rem;
}
.card h4 {
  margin: 0 0 0.45rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
}

.stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.stat {
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0.75rem 1rem;
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
  border-top: 3px solid var(--c, var(--teal));
}
.stat b {
  display: block;
  font-size: 1.55rem;
  font-weight: 600;
  color: var(--text);
  line-height: 1.2;
}
.stat span {
  font-size: 0.72rem;
  color: var(--muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.cand {
  display: grid;
  grid-template-columns: 36px 72px 1fr;
  gap: 0.9rem;
  align-items: center;
  margin-bottom: 0.3rem;
}
.rank {
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--muted);
  text-align: center;
}
.score-box {
  width: 68px;
  padding: 4px 2px;
  border: 1px solid var(--border);
  border-radius: 4px;
  text-align: center;
  background: #FAFAF9;
}
.score-num {
  display: block;
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--teal);
  line-height: 1.1;
}
.score-den {
  font-size: 0.7rem;
  color: var(--muted);
  font-weight: 500;
}
.ctitle {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 0.15rem;
}
.why {
  color: var(--muted);
  font-size: 0.88rem;
  margin-bottom: 0.35rem;
}

.pill {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  margin-left: 0.5rem;
  vertical-align: middle;
}
.pill.strong { background: #F0FDF4; color: #15803D; border: 1px solid #BBF7D0; }
.pill.pot { background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
.pill.weak { background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }

.chip {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  margin: 2px 4px 2px 0;
  border: 1px solid transparent;
}
.chip.ok { background: #F0FDF4; color: #15803D; border-color: #BBF7D0; }
.chip.miss { background: #FEF2F2; color: #B91C1C; border-color: #FECACA; }
.chip.bonus { background: #F0FDFA; color: #0F766E; border-color: #99F6E4; }
.chip.gray { background: #F5F5F4; color: #44403C; border-color: #E7E5E4; }

.bars {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.8rem;
  margin-top: 0.45rem;
}
.bl {
  font-size: 0.72rem;
  color: var(--muted);
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.15rem;
}
.bar {
  height: 6px;
  border-radius: 2px;
  background: #E7E5E4;
  overflow: hidden;
}
.bar i {
  display: block;
  height: 100%;
  border-radius: 2px;
  background: var(--teal);
}

.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.tbl th {
  text-align: left;
  background: #F5F5F4;
  color: #44403C;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.45rem 0.6rem;
  border-bottom: 1px solid var(--border);
}
.tbl td {
  padding: 0.45rem 0.6rem;
  border-bottom: 1px solid #E7E5E4;
  color: var(--text);
}
.tbl tr:last-child td {
  border-bottom: none;
}

.steps {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.step {
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0.85rem;
}
.step .n {
  width: 22px;
  height: 22px;
  border-radius: 3px;
  background: var(--teal);
  color: #FFFFFF;
  font-weight: 600;
  font-size: 0.8rem;
  display: grid;
  place-items: center;
  margin-bottom: 0.35rem;
}
.step b { color: var(--text); font-size: 0.9rem; font-weight: 600; }
.step p { font-size: 0.8rem; color: var(--muted); margin: 0.2rem 0 0; }

.arch {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.6rem;
  text-align: center;
}
.arch div {
  padding: 0.75rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
  color: #FFFFFF;
  font-size: 0.85rem;
}
.arch small {
  display: block;
  font-weight: 400;
  opacity: 0.9;
  margin-top: 0.2rem;
}

.mode {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 0.6rem;
  background: #F0FDFA;
  color: var(--teal);
  border: 1px solid #99F6E4;
}

div[data-testid="stTabs"] [data-baseweb="tab-list"] {
  border-bottom: 1px solid var(--border);
  gap: 1rem;
  background: transparent;
}
button[data-baseweb="tab"] {
  font-weight: 600;
  font-size: 0.92rem;
  color: var(--muted);
  border: none;
  background: transparent;
  padding: 0.45rem 0.3rem;
  border-radius: 0;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--teal) !important;
  border-bottom: 2px solid var(--teal) !important;
}

div.stButton > button {
  border-radius: 4px;
  font-weight: 500;
  border: 1px solid var(--border);
  background: #FFFFFF;
  color: var(--text);
  width: 100%;
  padding: 0.4rem 0.8rem;
  transition: all 0.1s ease;
}
div.stButton > button:hover {
  border-color: var(--teal);
  color: var(--teal);
  background: #F0FDFA;
}
div.stDownloadButton > button {
  border-radius: 4px;
  font-weight: 500;
  border: 1px solid var(--teal);
  background: #FFFFFF;
  color: var(--teal);
  width: 100%;
  padding: 0.4rem 0.8rem;
}
div.stDownloadButton > button:hover {
  background: var(--teal);
  color: #FFFFFF;
}
button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background: var(--accent) !important;
  color: #FFFFFF !important;
  border: 1px solid var(--accent-hover) !important;
  border-radius: 4px !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 2px rgba(0,0,0,.08) !important;
}
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
  background: var(--accent-hover) !important;
  color: #FFFFFF !important;
}

[data-testid="stChatMessage"] {
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0.75rem 0.9rem;
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
}

.foot {
  text-align: center;
  color: var(--muted);
  font-size: 0.78rem;
  margin: 1.5rem 0 0.5rem;
  padding-top: 0.6rem;
  border-top: 1px solid var(--border);
}

@media (max-width:900px) {
  .stats, .steps, .arch { grid-template-columns: 1fr 1fr; }
  .bars { grid-template-columns: 1fr; }
  .cand { grid-template-columns: 30px 65px 1fr; }
}
</style>""", unsafe_allow_html=True)


def chips(items, cls): return "".join(f'<span class="chip {cls}">{esc(i)}</span>' for i in items)


def table(rows):
    if not rows: return ""
    th = "".join(f"<th>{esc(str(k))}</th>" for k in rows[0])
    tb = "".join("<tr>" + "".join(f"<td>{esc(str(v))}</td>" for v in r.values()) + "</tr>" for r in rows)
    return f'<div class="card" style="padding:.4rem .7rem;overflow-x:auto"><table class="tbl"><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>'


def card(rank, c, ctx):
    p, m = c["pts"], c["max"]
    bars = "".join(f'<div><div class="bl"><span>{n}</span><span>{p[k]:.0f}/{m[k]:.0f}</span></div><div class="bar"><i style="width:{100 * p[k] / m[k] if m[k] else 0:.0f}%"></i></div></div>'
                   for n, k in [("Skills", "skills"), ("Semantic", "semantic"), ("Experience", "experience")])
    warn = f'<div class="why">⚠️ {esc(c["warn"])}</div>' if c["warn"] else ""
    return (f'<div class="card"><div class="cand"><div class="rank">#{rank}</div>'
            f'<div class="score-box"><span class="score-num">{c["score"]:.0f}</span><span class="score-den">/100</span></div>'
            f'<div><div class="ctitle">{esc(A.label(ctx, c))}<span class="pill {PILL[c["verdict"]]}">{c["verdict"]}</span></div><div class="why">{esc(c["why"])}</div>{warn}'
            f'<div>{chips(c["req_hit"], "ok")}{chips(c["req_miss"], "miss")}{chips(c["pref_hit"], "bonus")}</div><div class="bars">{bars}</div></div></div></div>')


# ── Header ──
st.markdown("""<div class="hero"><div class="eyebrow">AAILLM · Sanjivani College of Engineering · A.Y. 2026-27</div><h1>Resume Screening Copilot</h1>
<p>An agentic AI assistant that reads, scores and ranks resumes against a job description with explainable decisions.</p></div>""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("### Copilot settings")
    st.caption("SCORING WEIGHTS")
    ws, wm, we = st.slider("Skills match", 0, 100, 55), st.slider("Semantic similarity (TF-IDF)", 0, 100, 20), st.slider("Experience", 0, 100, 25)
    tw = (ws + wm + we) or 1
    st.caption(f"Normalised → {ws / tw:.0%} skills · {wm / tw:.0%} semantic · {we / tw:.0%} experience")
    bias = st.toggle("Bias-aware mode", True, help="Masks name, email, phone, links and he/she before scoring. Candidates appear as C1, C2… until shortlisted.")
    st.divider()
    st.caption("GENAI MODE (OPTIONAL)")
    key = st.text_input("Anthropic API key", os.getenv("ANTHROPIC_API_KEY", ""), type="password", help="Leave empty to use the offline rule-based agent.")
    model = st.text_input("Claude model", os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"))
    st.info("Verdict: **70+** Strong · **50–69** Potential · **<50** Weak.\n\nNo one is rejected automatically — the recruiter decides.")

t_screen, t_res, t_chat, t_about = st.tabs(["Screen resumes", "Ranked results", "Copilot chat", "About"])

# ── Screen resumes ──
with t_screen:
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.markdown("#### Resumes")
        src = st.radio("Source", ["Bundled sample resumes (5)", "Upload my own"], horizontal=True, label_visibility="collapsed")
        ups = st.file_uploader("PDF, DOCX or TXT", type=["pdf", "docx", "txt"], accept_multiple_files=True) if src.startswith("Upload") else []
        if not ups and src.startswith("Upload"): st.caption("Upload one or more resumes to continue.")
        if src.startswith("Bundled"): st.caption("Five fictional resumes: a GenAI engineer, a fresher, a data analyst, a full-stack dev and an AI engineer.")
    with right:
        st.markdown("#### Job description")
        jd = st.text_area("JD", (SAMPLES / "job_description.txt").read_text(), height=290, label_visibility="collapsed",
                          help="Put skills under 'Required skills' and 'Preferred skills' headings for best results.")
    if st.button("Screen resumes", type="primary"):
        files = [(p.name, p.read_bytes()) for p in sorted((SAMPLES / "resumes").glob("*.txt"))] if src.startswith("Bundled") else [(u.name, u.getvalue()) for u in ups]
        cands = []
        for i, (n, d) in enumerate(files, 1):
            try: cands.append(E.make_candidate(len(cands) + 1, n, d))
            except Exception as e: st.warning(f"Could not read {n}: {e}")
        job = E.parse_job(jd)
        if not cands: st.error("Add at least one resume first.")
        elif not job["required"] and not job["preferred"]: st.error("No known skills found in the job description. Add a 'Required skills' list.")
        else:
            for k in [k for k in st.session_state if str(k).startswith("sl_")]: del st.session_state[k]
            st.session_state.update(raw=cands, job=job, chat=[], last=None)
            st.success(f"Screened **{len(cands)} resumes** against **{job['title']}** — open **Ranked results** or **Copilot chat**.")

# ── Scoring (re-runs when weights / bias change) ──
raw, job = st.session_state.get("raw"), st.session_state.get("job")
ctx = None
if raw:
    E.score_all(raw, job, {"skills": ws, "semantic": wm, "experience": we}, bias)
    short = {c["id"] for c in raw if st.session_state.get(f"sl_{c['id']}")}
    ctx = {"cands": raw, "job": job, "bias": bias, "reveal": short, "last": st.session_state.get("last")}
    ranked = sorted(raw, key=lambda c: -c["score"])

# ── Ranked results ──
with t_res:
    if not ctx: st.info("Run a screening in the **Screen resumes** tab to see ranked candidates here.")
    else:
        cnt = {v: sum(c["verdict"] == v for c in raw) for v in COL}
        st.markdown('<div class="stats">' + "".join(f'<div class="stat" style="--c:{c}"><b>{v}</b><span>{l}</span></div>' for l, v, c in [
            ("Screened", len(raw), "#0F766E"), ("Strong match", cnt["Strong match"], COL["Strong match"]), ("Potential", cnt["Potential"], COL["Potential"]),
            ("Weak match", cnt["Weak match"], COL["Weak match"]), ("Average score", f"{sum(c['score'] for c in raw) / len(raw):.0f}", "#EA580C")]) + "</div>", unsafe_allow_html=True)
        st.markdown(f'<div class="card"><h4>{esc(job["title"])} · {job["min_years"]:g}+ years</h4><b>Required</b> &nbsp;{chips(job["required"], "gray")}<br><b>Preferred</b> &nbsp;{chips(job["preferred"], "gray")}</div>', unsafe_allow_html=True)
        st.markdown(f'<span class="chip ok">Matched required</span><span class="chip miss">Not mentioned (verify)</span><span class="chip bonus">Bonus skill</span>', unsafe_allow_html=True)
        for i, c in enumerate(ranked, 1):
            st.markdown(card(i, c, ctx), unsafe_allow_html=True)
            a, b = st.columns([1, 3])
            a.checkbox("Shortlist", key=f"sl_{c['id']}", help="Shortlisting reveals the identity in bias-aware mode.")
            if bias and c["id"] in short:
                ct = E.contacts(c["text"]); b.caption(f"**{c['name']}** · {ct['email']} · {ct['phone']} · _{c['file']}_")
        st.markdown("#### Score composition")
        st.bar_chart(pd.DataFrame([{"Candidate": A.label(ctx, c), "Skills": c["pts"]["skills"], "Semantic": c["pts"]["semantic"], "Experience": c["pts"]["experience"]} for c in ranked]).set_index("Candidate"),
                     color=["#0F766E", "#EA580C", "#78716C"])
        df = pd.DataFrame([{"Rank": i, "Candidate": A.label(ctx, c), "Score": c["score"], "Verdict": c["verdict"], "Shortlisted": c["id"] in short,
                            "Matched required": ", ".join(c["req_hit"]), "Missing required": ", ".join(c["req_miss"]), "Bonus": ", ".join(c["pref_hit"]), "Years": c["yrs"]} for i, c in enumerate(ranked, 1)])
        d1, d2 = st.columns(2)
        d1.download_button("Download full ranking (CSV)", df.to_csv(index=False), "ranking.csv", "text/csv")
        d2.download_button("Download shortlist only (CSV)", df[df.Shortlisted].to_csv(index=False), "shortlist.csv", "text/csv", disabled=not short)

# ── Copilot chat ──
with t_chat:
    if not ctx: st.info("Run a screening first — the copilot answers from the real screening data.")
    else:
        st.markdown(f'<span class="mode">{"GenAI mode · Claude tool-use" if key else "Offline mode · rule-based agent"}</span>', unsafe_allow_html=True)
        best = ranked[0]["id"]
        sug = ["Who should I interview first?", "Show the top 3", "Skill gaps in the pool", f"Compare {ranked[0]['id']} and {ranked[1]['id']}" if len(ranked) > 1 else "Show all candidates",
               f"Interview questions for {best}", f"Draft an invite for {best}"]
        for i, col in enumerate(st.columns(3)):
            for j in (i, i + 3): col.button(sug[j], key=f"sg{j}", on_click=lambda s=sug[j]: st.session_state.update(pending=s))
        box = st.container()
        q = st.chat_input("Ask the copilot… e.g. “compare C1 and C5” or “who has Docker?”") or st.session_state.pop("pending", None)
        chat = st.session_state.setdefault("chat", [])
        if q:
            hist = [{"role": m["role"], "content": m["content"]} for m in chat]
            chat.append({"role": "user", "content": q})
            with st.spinner("Copilot is working…"): res = A.answer(ctx, q, hist, key, model)
            chat.append({"role": "assistant", "content": res["answer"], **{k: res[k] for k in ("table", "chart", "steps", "follow", "mode")}})
            st.session_state.last = ctx["last"]
        with box:
            if not chat: st.markdown(f"Screening copilot ready. Screened **{len(raw)} resumes** for **{esc(job['title'])}**. Pick a suggestion above or ask me anything.")
            for m in chat:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])
                    if m["role"] == "assistant":
                        if m.get("table"): st.markdown(table(m["table"]), unsafe_allow_html=True)
                        if m.get("chart"): st.bar_chart(pd.Series(m["chart"], name="value"), color="#0F766E")
                        if m.get("steps"):
                            with st.expander("Agent steps"):
                                for n, s in enumerate(m["steps"], 1): st.markdown(f"{n}. `{s['tool']}({', '.join(f'{k}={v!r}' for k, v in s['args'].items())})`")
            if chat and chat[-1]["role"] == "assistant" and chat[-1].get("follow"):
                st.caption("Suggested follow-ups")
                for i, f in enumerate(chat[-1]["follow"][:3]): st.button(f, key=f"fu{len(chat)}_{i}", on_click=lambda s=f: st.session_state.update(pending=s))

# ── About ──
with t_about:
    st.markdown("#### How it works")
    st.markdown('<div class="steps">' + "".join(f'<div class="step"><div class="n">{n}</div><b>{t}</b><p>{d}</p></div>' for n, t, d in [
        (1, "Upload", "PDF, DOCX or TXT resumes and a job description"), (2, "Parse", "Text, skills and years of experience; identity masked"),
        (3, "Analyse job", "Required and preferred skills, minimum years"), (4, "Match", "Weighted score out of 100"),
        (5, "Review", "Ranked list, reasons and copilot chat; recruiter decides")]) + "</div>", unsafe_allow_html=True)
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("#### Scoring formula")
        st.markdown('<div class="card"><b>Score = 55% Skills + 20% Semantic + 25% Experience</b><br><br><span class="chip ok">Skills</span> required skills count double, preferred once<br>'
                    '<span class="chip bonus">Semantic</span> TF-IDF cosine similarity between resume and JD<br><span class="chip miss">Experience</span> years from work date ranges vs the required years (education dates ignored)<br><br>'
                    'The same resume and settings always give the same score.</div>', unsafe_allow_html=True)
        st.markdown("#### Fair and secure")
        st.markdown('<div class="card">• Name, email, phone, links and pronouns are masked before scoring<br>• Candidates appear as C1, C2… until shortlisted<br>• No automatic rejection — the recruiter decides<br>• Processed in the session only; no database or file storage</div>', unsafe_allow_html=True)
    with b:
        st.markdown("#### Architecture")
        st.markdown('<div class="card"><div class="arch"><div style="background:#0F766E">Streamlit UI<small>presentation tier</small></div><div style="background:#115E59">Agent<small>Claude or offline</small></div>'
                    '<div style="background:#134E4A">8 tools<small>shortlist · compare · …</small></div><div style="background:#44403C">Core engine<small>parse · skills · score</small></div></div></div>', unsafe_allow_html=True)
        st.markdown("#### Agent tools")
        st.markdown('<div class="card">' + chips(list(A.TOOLS), "bonus") + "</div>", unsafe_allow_html=True)
        st.markdown("#### Limits (stated honestly)")
        st.markdown('<div class="card">Skill dictionary is limited (~70 skills) · scanned PDFs need OCR · experience is estimated from dates and phrases · semantic part is TF-IDF, not neural embeddings. <b>Academic prototype — not a certified hiring tool.</b></div>', unsafe_allow_html=True)

st.markdown('<div class="foot">Resume Screening Copilot · AAILLM · Dept. of Information Technology, Sanjivani College of Engineering, Kopargaon</div>', unsafe_allow_html=True)
