"""Agentic copilot: 8 tools over the screening data, an offline rule-based agent and a Claude tool-use loop."""
import json, re
import engine as E

# ctx = {"cands": [...], "job": {...}, "bias": bool, "reveal": set of ids, "last": id or None}


def _rank(ctx): return sorted(ctx["cands"], key=lambda c: -c["score"])
def label(ctx, c): return c["name"] if (not ctx["bias"] or c["id"] in ctx["reveal"]) else c["id"]


def _find(ctx, cid):
    m = re.search(r"\d+", str(cid))
    return next((c for c in ctx["cands"] if m and c["id"] == "C" + m.group()), None)


def _row(ctx, i, c): return {"Rank": i, "Candidate": label(ctx, c), "Score": c["score"], "Verdict": c["verdict"], "Why": c["why"]}
def _miss(cid): return {"text": f"I couldn't find a candidate called '{cid}'. Use IDs like C1, C2…"}
def _join(x): return ", ".join(x) if x else "none"


# ── The 8 tools ──
def shortlist(ctx, top_n=3):
    r = _rank(ctx)[:max(1, int(top_n))]
    best = r[0]["id"]
    return {"text": f"Top {len(r)} of {len(ctx['cands'])} candidates by match score:", "table": [_row(ctx, i, c) for i, c in enumerate(r, 1)],
            "chart": {label(ctx, c): c["score"] for c in r}, "follow": ["Who should I interview first?", f"Interview questions for {best}", "Skill gaps in the pool"]}


def recommend(ctx):
    r = _rank(ctx); b = r[0]; ctx["last"] = b["id"]
    t = f"**{label(ctx, b)}** is the strongest match: **{b['score']}/100 ({b['verdict']})** — {b['why']}."
    if b["req_miss"]: t += f" Not mentioned in the resume: {_join(b['req_miss'])} (verify in the interview)."
    if len(r) > 1: t += f" Runner-up: {label(ctx, r[1])} ({r[1]['score']})."
    return {"text": t + " This is advice only — the final decision is yours.",
            "follow": [f"Interview questions for {b['id']}", f"Draft an invite for {b['id']}", "Compare the top two"]}


def get_candidate(ctx, candidate_id):
    c = _find(ctx, candidate_id)
    if not c: return _miss(candidate_id)
    ctx["last"] = c["id"]; p, m = c["pts"], c["max"]
    t = (f"**{label(ctx, c)}** — {c['score']}/100 · {c['verdict']}\n"
         f"- Required skills matched ({len(c['req_hit'])}/{len(ctx['job']['required'])}): {_join(c['req_hit'])}\n"
         f"- Not mentioned (verify): {_join(c['req_miss'])}\n- Bonus skills: {_join(c['pref_hit'])}\n"
         f"- Experience: {c['yrs']:g} yrs vs {ctx['job']['min_years']:g} required\n"
         f"- Score breakdown: skills {p['skills']:.0f}/{m['skills']:.0f}, semantic {p['semantic']:.0f}/{m['semantic']:.0f}, experience {p['experience']:.0f}/{m['experience']:.0f}")
    return {"text": t, "follow": [f"Interview questions for {c['id']}", f"Draft an invite for {c['id']}"]}


def compare(ctx, candidate_a, candidate_b):
    a, b = _find(ctx, candidate_a), _find(ctx, candidate_b)
    if not a or not b: return _miss(f"{candidate_a} / {candidate_b}")
    ctx["last"] = a["id"]
    rows = [{"Metric": k, label(ctx, a): f(a), label(ctx, b): f(b)} for k, f in [
        ("Score", lambda c: c["score"]), ("Verdict", lambda c: c["verdict"]),
        ("Required skills", lambda c: f"{len(c['req_hit'])}/{len(ctx['job']['required'])}"),
        ("Missing required", lambda c: _join(c["req_miss"])), ("Bonus skills", lambda c: _join(c["pref_hit"])),
        ("Experience (yrs)", lambda c: c["yrs"]), ("Skills pts", lambda c: round(c["pts"]["skills"], 1)),
        ("Semantic pts", lambda c: round(c["pts"]["semantic"], 1)), ("Experience pts", lambda c: round(c["pts"]["experience"], 1))]]
    w = a if a["score"] >= b["score"] else b
    return {"text": f"**{label(ctx, w)}** leads by {abs(a['score'] - b['score']):.1f} points.", "table": rows,
            "chart": {label(ctx, a): a["score"], label(ctx, b): b["score"]}, "follow": [f"Interview questions for {w['id']}", "Skill gaps in the pool"]}


def find_by_skill(ctx, skill):
    name = (E.extract_skills(skill) or [skill.strip()])[0]
    hits = [c for c in _rank(ctx) if name.lower() in {s.lower() for s in c["skills"]}]
    rows = [{"Candidate": label(ctx, c), "Score": c["score"], "Verdict": c["verdict"]} for c in hits]
    return {"text": f"**{len(hits)}** of {len(ctx['cands'])} candidates mention **{name}**." + ("" if hits else " A gap means 'not mentioned in the resume'."),
            "table": rows or None, "follow": ["Show the top 3", "Skill gaps in the pool"]}


def skill_gap_summary(ctx):
    n, req = len(ctx["cands"]), ctx["job"]["required"]
    cnt = {k: sum(k in c["skills"] for c in ctx["cands"]) for k in req}
    rows = [{"Required skill": k, "Candidates with it": v, "Coverage": f"{v}/{n}"} for k, v in sorted(cnt.items(), key=lambda x: x[1])]
    rare = [k for k, v in cnt.items() if v == min(cnt.values())] if cnt else []
    return {"text": f"Scarcest required skills in this pool: **{_join(rare)}** ({min(cnt.values()) if cnt else 0}/{n} candidates). "
                    "A gap means *not mentioned*, not *not possessed* — verify with the candidate.",
            "table": rows, "chart": cnt, "follow": ["Show the top 3", "Who should I interview first?"]}


_Q = {"RAG": "Walk me through how you would build a RAG pipeline: chunking, embeddings, retrieval, re-ranking and how you would evaluate answer quality.",
      "LLMs": "How do you decide between prompting, fine-tuning and retrieval for an LLM task? What failure modes have you seen?",
      "Prompt Engineering": "How do you version, test and evaluate prompts so changes don't silently regress quality?",
      "FastAPI": "How would you design a FastAPI service that streams LLM output and handles concurrency, auth and timeouts?",
      "Python": "Describe a Python codebase you maintained: how did you structure, test and profile it?",
      "SQL": "Write (or describe) a query to find the top 3 items per category. How would you optimise it on a large table?",
      "Docker": "How do you keep Docker images small, reproducible and secure? What goes into your Dockerfile and compose setup?",
      "Machine Learning": "Pick a model you trained end to end: how did you choose metrics, avoid leakage and decide it was good enough?",
      "Git": "How does your team use branching and code review? Tell us about a difficult merge you resolved."}


def interview_questions(ctx, candidate_id):
    c = _find(ctx, candidate_id)
    if not c: return _miss(candidate_id)
    ctx["last"] = c["id"]; qs = []
    for s in c["req_hit"][:3]: qs.append(f"**Verify {s}:** " + _Q.get(s, f"Tell me about a project where you used {s}. What was your own contribution and what trade-offs did you make?"))
    for s in c["req_miss"][:3]: qs.append(f"**Probe gap — {s}:** Your resume doesn't mention {s}. Have you used it or something similar, and how would you get up to speed?")
    if c["yrs"] < ctx["job"]["min_years"]: qs.append(f"**Experience:** The role asks for {ctx['job']['min_years']:g}+ years; walk us through the most complex work you have owned so far.")
    qs.append("**Collaboration:** Describe a time you disagreed with a teammate on a technical decision. How was it resolved?")
    return {"text": f"Tailored interview questions for **{label(ctx, c)}**:\n\n" + "\n".join(f"{i}. {q}" for i, q in enumerate(qs, 1)),
            "follow": [f"Draft an invite for {c['id']}", "Show the top 3"]}


def draft_email(ctx, candidate_id, kind="invite"):
    c = _find(ctx, candidate_id)
    if not c: return _miss(candidate_id)
    ctx["last"] = c["id"]; job = ctx["job"]["title"]
    nm = label(ctx, c); to = "[Candidate name]" if nm == c["id"] else nm
    if kind == "rejection":
        subj, body = f"Your application for {job}", (f"Dear {to},\n\nThank you for your interest in the {job} role and for the time you put into your application. "
                      "After careful review we have decided not to move forward at this stage. We will keep your profile on file and encourage you to apply for future openings.\n\nBest wishes,\n[Recruiter name]")
    else:
        subj, body = f"Interview invitation — {job}", (f"Dear {to},\n\nThank you for applying for the {job} role. We were impressed by your background"
                      f"{' in ' + ', '.join(c['req_hit'][:3]) if c['req_hit'] else ''} and would like to invite you to an interview. "
                      "Please reply with two or three time slots that suit you this week.\n\nWarm regards,\n[Recruiter name]")
    return {"text": f"Draft **{kind}** email for **{nm}** — review before sending (a human makes the decision):\n\n**Subject:** {subj}\n\n{body}", "follow": ["Show the top 3"]}


_I, _S = "integer", "string"
TOOLS = {  # name: (function, description, {param: (type, description)}, required)
    "shortlist": (shortlist, "Rank candidates by match score and return the top N with reasons.", {"top_n": (_I, "How many candidates (default 3)")}, []),
    "recommend": (recommend, "Recommend which single candidate to interview first and why.", {}, []),
    "get_candidate": (get_candidate, "Explain one candidate: matched/missing skills, experience, score breakdown.", {"candidate_id": (_S, "e.g. C1")}, ["candidate_id"]),
    "compare": (compare, "Compare two candidates side by side.", {"candidate_a": (_S, "e.g. C1"), "candidate_b": (_S, "e.g. C2")}, ["candidate_a", "candidate_b"]),
    "find_by_skill": (find_by_skill, "Find which candidates mention a given skill.", {"skill": (_S, "e.g. Docker")}, ["skill"]),
    "skill_gap_summary": (skill_gap_summary, "Show which required skills are scarce across the whole candidate pool.", {}, []),
    "interview_questions": (interview_questions, "Generate tailored interview questions for a candidate.", {"candidate_id": (_S, "e.g. C1")}, ["candidate_id"]),
    "draft_email": (draft_email, "Draft an interview-invite or rejection email for a candidate.", {"candidate_id": (_S, "e.g. C1"), "kind": (_S, "'invite' or 'rejection'")}, ["candidate_id"]),
}
SCHEMAS = [{"name": n, "description": d, "input_schema": {"type": "object", "required": r, "properties": {k: {"type": t, "description": ds} for k, (t, ds) in p.items()}}}
           for n, (_, d, p, r) in TOOLS.items()]


def run_tool(ctx, name, args):
    try: return TOOLS[name][0](ctx, **args)
    except Exception as e: return {"text": f"Tool error: {e}"}


# ── Offline rule-based agent (same tools, no API key) ──
HELP = ("I can **rank** candidates, **recommend** who to interview first, **explain** or **compare** candidates, find who has a **skill**, "
        "show **skill gaps**, write **interview questions** and **draft emails**. Try: *“Compare C1 and C2”* or *“Who has Docker?”*")


def offline(ctx, q):
    ql = q.lower(); ids = ["C" + n for n in re.findall(r"\bc(\d+)\b", ql)]
    if not ids and re.search(r"\b(him|her|them|he|she|his|this candidate|that candidate)\b", ql) and ctx.get("last"): ids = [ctx["last"]]
    r = _rank(ctx); cid = ids[0] if ids else (ctx.get("last") or r[0]["id"]); sk = E.extract_skills(q)
    n = re.search(r"(?:top|first)\s*(\d+)|(\d+)\s*(?:best|top)", ql)
    if re.search(r"e-?mail|invite|reject|decline", ql): call = ("draft_email", {"candidate_id": cid, "kind": "rejection" if re.search(r"reject|decline|regret", ql) else "invite"})
    elif "question" in ql: call = ("interview_questions", {"candidate_id": cid})
    elif re.search(r"compar|\bvs\b|versus|difference", ql):
        p = (ids + [x["id"] for x in r])[:2] if len(ids) < 2 else ids[:2]; call = ("compare", {"candidate_a": p[0], "candidate_b": p[1]})
    elif re.search(r"gap|missing|lack|scarce", ql) and not ids: call = ("skill_gap_summary", {})
    elif sk and re.search(r"who|which|find|know|has|have|with|skill", ql): call = ("find_by_skill", {"skill": sk[0]})
    elif re.search(r"interview first|who should|best|recommend|strongest|pick|hire", ql): call = ("recommend", {})
    elif re.search(r"short ?list|top|rank|list|leaderboard|all candidates", ql): call = ("shortlist", {"top_n": int(n.group(1) or n.group(2)) if n else (len(r) if "all" in ql else 3)})
    elif ids: call = ("get_candidate", {"candidate_id": ids[0]})
    else: return {"answer": HELP, "steps": [], "table": None, "chart": None, "follow": ["Who should I interview first?", "Show the top 3"], "mode": "offline"}
    out = run_tool(ctx, *call)
    return {"answer": out["text"], "steps": [{"tool": call[0], "args": call[1]}], "table": out.get("table"), "chart": out.get("chart"), "follow": out.get("follow", []), "mode": "offline"}


# ── Claude tool-use loop (optional API key) ──
SYSTEM = ("You are Resume Screening Copilot, an assistant for recruiters. ALWAYS use the tools to answer from the real screening data; never guess scores or skills. "
          "Candidates may be anonymised (C1, C2…): never try to infer identity, gender or age. A skill gap means 'not mentioned in the resume', so suggest verifying it. "
          "Never reject anyone automatically — you give advice and the recruiter decides. Keep answers short and clear, in Markdown. "
          "If a tool already returns a table, don't repeat all its rows in prose.")


def claude(ctx, q, hist, key, model):
    import anthropic
    cl = anthropic.Anthropic(api_key=key)
    msgs, steps, table, chart, follow = list(hist) + [{"role": "user", "content": q}], [], None, None, []
    for _ in range(6):
        r = cl.messages.create(model=model, max_tokens=1500, system=SYSTEM, tools=SCHEMAS, messages=msgs)
        msgs.append({"role": "assistant", "content": r.content})
        if r.stop_reason != "tool_use": break
        res = []
        for b in r.content:
            if b.type == "tool_use":
                out = run_tool(ctx, b.name, b.input); steps.append({"tool": b.name, "args": dict(b.input)})
                table, chart, follow = out.get("table") or table, out.get("chart") or chart, out.get("follow") or follow
                res.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, default=str)})
        msgs.append({"role": "user", "content": res})
    text = "".join(b.text for b in r.content if b.type == "text") or "Done."
    return {"answer": text, "steps": steps, "table": table, "chart": chart, "follow": follow, "mode": "claude"}


def answer(ctx, q, hist=(), key="", model="claude-sonnet-5-5"):
    if key:
        try: return claude(ctx, q, list(hist), key, model)
        except Exception as e:
            out = offline(ctx, q); out["answer"] = f"⚠️ Claude API unavailable ({type(e).__name__}) — used the offline agent.\n\n" + out["answer"]; return out
    return offline(ctx, q)
