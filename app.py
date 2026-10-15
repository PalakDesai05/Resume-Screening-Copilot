import os, re, time, pandas as pd, streamlit as st
from copilot.parser import parse_resume, read_file
from copilot.scorer import parse_jd, score_all
from copilot.agent import Screening, run_llm_agent, run_offline_agent, llm_available

st.set_page_config(page_title="Resume Screening Copilot", page_icon="🧭", layout="wide")
st.markdown("""<style>
[data-testid='stAppDeployButton'],.stAppDeployButton,.stDeployButton{display:none!important}
.hero{background:linear-gradient(135deg,#6a5cff 0%,#00b3ff 60%,#00d4aa 100%);padding:20px 28px;border-radius:18px;color:#fff;margin-bottom:10px}
.hero h1{margin:0;font-size:1.7rem;color:#fff;padding:0}.hero p{margin:4px 0 0;opacity:.92}
div[data-testid='stButton']>button{border-radius:999px}
</style>""", unsafe_allow_html=True)

SAMPLE_JD = "sample_data/sample_jd.txt"; SAMPLE_DIR = "sample_data/resumes"
QUICK = ["Who should I interview first?", "Top 3 candidates", "What is skill gap?", "How is score calculated?"]

def greeting(jd, ranked):
    st_ = Screening(jd, ranked); g = st_.skill_gap_summary()
    title = next((l.strip() for l in jd.text.splitlines() if l.strip()), "the role")
    strong = sum(c.result["verdict"] == "Strong match" for c in ranked); top = ranked[0]
    gaps = {k: v for k, v in g["pct_missing_each_required"].items() if v}
    msg = (f"👋 Hi! I screened **{len(ranked)} resume(s)** for **{title}**.\n\n"
           f"- 🏆 Best match: **{top.cid}** with score **{top.result['score']}** ({top.result['verdict']})\n"
           f"- ✅ Strong matches: **{strong}**\n")
    if gaps: k = max(gaps, key=gaps.get); msg += f"- ⚠️ Biggest skill gap in the pool: **{k}** (missing in {gaps[k]}% of candidates)\n"
    return msg + "\nWhat would you like to know?"

def screen(text, raw, weights):
    jd = parse_jd(text); cands = [parse_resume(i + 1, n, b) for i, (n, b) in enumerate(raw)]
    t = sum(weights) or 1; ranked = score_all(jd, cands, tuple(w / t for w in weights))
    st.session_state.update(jd=jd, ranked=ranked, last_id=None, greet_msg=greeting(jd, ranked))
    reset_chat()

def reset_chat():
    st.session_state.chat = [dict(role="assistant", content=st.session_state.greet_msg, greet=True, trace=[])]

def load_samples():
    return [(n, open(f"{SAMPLE_DIR}/{n}", "rb").read()) for n in sorted(os.listdir(SAMPLE_DIR))] if os.path.isdir(SAMPLE_DIR) else []

# ---------------- sidebar ----------------
with st.sidebar:
    st.header("📄 Job description")
    jd_file = st.file_uploader("Upload JD (txt/pdf/docx)", type=["txt", "pdf", "docx"])
    jd_text = st.text_area("…or paste JD", value=open(SAMPLE_JD).read() if os.path.exists(SAMPLE_JD) else "", height=200)
    st.header("👥 Resumes")
    files = st.file_uploader("Upload resumes (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"], accept_multiple_files=True)
    use_samples = st.checkbox("Use bundled sample resumes", value=not files)
    st.header("⚙️ Settings")
    anon = st.toggle("Bias-aware mode (anonymise profiles)", value=True, help="ON: candidates appear as C1, C2… (C1 = upload order, NOT rank); names/contacts are hidden and removed before scoring.")
    w_s = st.slider("Weight: skills", 0, 100, 55); w_m = st.slider("Weight: semantic fit", 0, 100, 20); w_e = st.slider("Weight: experience", 0, 100, 25)
    with st.expander("Advanced: LLM agent (optional)"):
        st.caption("Not needed. Adds free-form Claude chat. Leave empty to use the built-in offline copilot.")
        key = st.text_input("Anthropic API key", type="password", value=os.getenv("ANTHROPIC_API_KEY", ""))
    go = st.button("🚀 Screen candidates", type="primary", use_container_width=True)

if go:
    text = read_file(jd_file.name, jd_file.getvalue()) if jd_file else jd_text
    raw = [(f.name, f.getvalue()) for f in files] if files else []
    if use_samples or not raw: raw += load_samples()
    if not text.strip() or not raw: st.error("Provide a job description and at least one resume.")
    else: screen(text, raw, (w_s, w_m, w_e))
if "ranked" not in st.session_state:
    if os.path.exists(SAMPLE_JD) and load_samples(): screen(open(SAMPLE_JD).read(), load_samples(), (55, 20, 25))
    else: st.info("Upload a JD and resumes in the sidebar, then click **Screen candidates**."); st.stop()

jd, ranked = st.session_state.jd, st.session_state.ranked
state = Screening(jd, ranked, anonymise=anon); state.last_id = st.session_state.get("last_id")
mode = "Claude agent" if llm_available(key) else "Offline copilot"
st.markdown(f"<div class='hero'><h1>🧭 Resume Screening Copilot</h1><p>Ask me about your candidates · I read, score, rank and explain · Mode: {mode}</p></div>", unsafe_allow_html=True)

# ---------------- helpers ----------------
def visuals(trace):
    done = set()
    for name, args in trace:
        if name in done: continue
        done.add(name)
        if name in ("shortlist", "find_by_skill"):
            rows = state.shortlist(args.get("top_n", 5)) if name == "shortlist" else state.find_by_skill(args.get("skill", ""))
            if rows: st.dataframe(pd.DataFrame([{"Rank": r["rank"], "Candidate": r["candidate"], "Score": r["score"], "Verdict": r["verdict"], "Exp (yrs)": r["years"]} for r in rows]),
                                  hide_index=True, column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f")})
        elif name in ("get_candidate", "recommend", "interview_questions", "draft_email"):
            d = state.get_candidate(args.get("candidate_id") or state.ranked[0].cid)
            if "error" in d or name in ("interview_questions", "draft_email"): continue
            c = st.columns(4); c[0].metric("Score", d["score"]); c[1].metric("Rank", f"#{d['rank']}"); c[2].metric("Verdict", d["verdict"]); c[3].metric("Experience", f"{d['years']:g} yrs")
            for k, v in d["score_breakdown"].items(): st.progress(min(v, 100) / 100, text=f"{k.title()} {v}%")
        elif name == "compare":
            ids = args.get("candidate_ids", []); cols = st.columns(max(len(ids), 1))
            for col, i in zip(cols, ids):
                d = state.get_candidate(i)
                if "error" not in d: col.metric(d["candidate"], d["score"], d["verdict"], delta_color="off")
        elif name == "skill_gap_summary":
            g = state.skill_gap_summary()
            if any(g["pct_missing_each_required"].values()): st.bar_chart(pd.Series(g["pct_missing_each_required"], name="% candidates missing"))

def last_id_from(trace):
    for name, a in reversed(trace):
        if a.get("candidate_id"): return a["candidate_id"].upper()
        if a.get("candidate_ids"): return a["candidate_ids"][0].upper()
        if name == "recommend": return state.ranked[0].cid
    return st.session_state.get("last_id")

def suggestions(trace):
    cid = st.session_state.get("last_id"); names = [n for n, _ in trace]; last = names[-1] if names else ""
    if last in ("recommend", "get_candidate") and cid: return [f"Interview questions for {cid}", f"Draft invite for {cid}", "Compare top 2 candidates"]
    if last == "interview_questions" and cid: return [f"Draft invite for {cid}", f"Why {cid}?", "Skill gaps in this pool"]
    if last == "draft_email" and cid: return [f"Interview questions for {cid}", "Top 3 candidates", "Skill gaps in this pool"]
    if last == "skill_gap_summary": return ["Who should I interview first?", "Top 3 candidates", "What is skill gap?"]
    if last in ("shortlist", "compare", "find_by_skill"): return ["Who should I interview first?", "Skill gaps in this pool", "Explain the top candidate"]
    return ["Who should I interview first?", "Top 3 candidates", "Skill gaps in this pool"]

def ask(text): st.session_state.pending = text
def stream(text):
    for tok in re.split(r"(\s+)", text): yield tok; time.sleep(0.01)

# ---------------- tabs ----------------
t_chat, t_dash = st.tabs(["💬 Copilot", "📊 Dashboard"])

with t_chat:
    top = st.columns([6, 1]); top[1].button("🗑 New chat", on_click=reset_chat, use_container_width=True)
    for m in st.session_state.chat:
        with st.chat_message(m["role"], avatar="🧭" if m["role"] == "assistant" else None):
            st.markdown(m["content"]); visuals(m.get("trace", []))
            if m.get("trace"):
                with st.expander("🛠 Agent steps (tools used)"):
                    for n, a in m["trace"]:
                        st.code(f"{n}({a})")
    typed = st.chat_input("Message Resume Screening Copilot…")
    q = typed or st.session_state.pop("pending", None)
    st.session_state._typing = bool(q)
    if len(st.session_state.chat) == 1 and not q:
        st.caption("Try asking")
        cols = st.columns(4)
        for i, qq in enumerate(QUICK): cols[i].button(qq, key=f"home{i}", on_click=ask, args=(qq,), use_container_width=True)
    if q:
        st.session_state.chat.append(dict(role="user", content=q, trace=[]))
        with st.chat_message("user"): st.markdown(q)
        with st.chat_message("assistant", avatar="🧭"):
            note = ""
            with st.spinner("Thinking…"):
                try:
                    if llm_available(key):
                        hist = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat if not m.get("greet")]
                        ans, trace = run_llm_agent(state, hist, api_key=key)
                    else: ans, trace = run_offline_agent(state, q)
                except Exception as e:
                    ans, trace = run_offline_agent(state, q)
                    note = "_API key invalid or LLM unreachable, so I answered with the offline copilot._\n\n" if ("401" in str(e) or "auth" in str(e).lower()) else "_LLM unavailable, using offline copilot._\n\n"
            ans = note + ans; st.write_stream(stream(ans)); visuals(trace)
            if trace:
                with st.expander("🛠 Agent steps (tools used)"):
                    for n, a in trace:
                        st.code(f"{n}({a})")
        st.session_state.last_id = last_id_from(trace)
        st.session_state.chat.append(dict(role="assistant", content=ans, trace=trace)); st.session_state.sugg = suggestions(trace)
    elif len(st.session_state.chat) > 1:
        st.session_state.setdefault("sugg", suggestions([]))
    if len(st.session_state.chat) > 1:
        cols = st.columns(3)
        for i, s_ in enumerate(st.session_state.get("sugg", [])[:3]): cols[i].button(s_, key=f"s{len(st.session_state.chat)}_{i}", on_click=ask, args=(s_,), use_container_width=True)

with t_dash:
    df = pd.DataFrame([{"Rank": i + 1, "ID": c.cid, "Candidate": c.cid if anon else c.name, "Score": c.result["score"], "Verdict": c.result["verdict"],
                        "Skills %": c.result["skill_score"], "Semantic %": c.result["semantic"], "Exp (yrs)": c.years, "Missing required": ", ".join(c.result["missing_required"])} for i, c in enumerate(ranked)])
    st.markdown(f"**Required:** {', '.join(jd.required) or '—'}  \n**Preferred:** {', '.join(jd.preferred) or '—'}  \n**Min experience:** {jd.min_years:g} yrs")
    st.dataframe(df, hide_index=True, column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f")})
    st.download_button("⬇ Export shortlist CSV", df.to_csv(index=False), "shortlist.csv", "text/csv")
    pick = st.selectbox("Candidate detail", [c.cid for c in ranked], format_func=lambda i: state.label(state.by_id[i]))
    c = state.by_id[pick]; r = c.result
    if anon and st.checkbox("🔓 Reveal identity (use only after shortlisting)"): st.info(f"**{c.name}** · {c.email or 'no email'} · {c.phone or 'no phone'} · file: {c.filename}")
    st.subheader("Why this score")
    for x in r["reasons"]:
        st.markdown("- " + x)
    st.markdown(f"✅ **Matched:** {', '.join(r['matched']) or '—'}  \n❌ **Missing required:** {', '.join(r['missing_required']) or 'none'}  \n➕ **Other skills:** {', '.join(r['extra_skills']) or '—'}")
    with st.expander("Resume text the model saw" + (" (anonymised)" if anon else "")): st.text(c.anon_text if anon else c.raw_text)
    g = state.skill_gap_summary(); st.subheader("Skill gaps")
    if any(g["pct_missing_each_required"].values()): st.bar_chart(pd.Series(g["pct_missing_each_required"], name="% candidates missing"))
    else: st.success("No required-skill gaps: every candidate has all required skills.")
