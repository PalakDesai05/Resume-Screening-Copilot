"""Agentic copilot: tool layer + Claude tool-use loop (with offline rule-based fallback)."""
import json, os, re
from .skills import extract_skills, TAXONOMY

class Screening:
    """Shared state the agent's tools operate on."""
    def __init__(self, jd, ranked, anonymise=True):
        self.jd, self.ranked, self.anonymise = jd, ranked, anonymise
        self.by_id = {c.cid: c for c in ranked}
        self.last_id = None  # conversation memory: last candidate discussed

    def label(self, c):
        return c.cid if self.anonymise else f"{c.cid} ({c.name})"

    def _summary(self, c):
        r = c.result
        return dict(candidate=self.label(c), rank=self.ranked.index(c) + 1, score=r["score"], verdict=r["verdict"],
                    years=r["years"], matched_skills=r["matched"], missing_required=r["missing_required"])

    # ---- tools ----
    def shortlist(self, top_n=5, min_score=0):
        return [self._summary(c) for c in self.ranked if c.result["score"] >= min_score][: int(top_n)]

    def get_candidate(self, candidate_id):
        c = self.by_id.get(candidate_id.upper())
        if not c: return {"error": f"Unknown candidate {candidate_id}. Valid: {list(self.by_id)}"}
        d = self._summary(c); r = c.result
        d.update(reasons=r["reasons"], education=r["education"], extra_skills=r["extra_skills"],
                 missing_preferred=r["missing_preferred"],
                 score_breakdown=dict(skills=r["skill_score"], semantic=r["semantic"], experience=r["exp_score"]))
        return d

    def compare(self, candidate_ids):
        return [self.get_candidate(i) for i in candidate_ids]

    def find_by_skill(self, skill):
        wanted = extract_skills(skill) or {skill}
        return [dict(self._summary(c), has=sorted(wanted & c.skills)) for c in self.ranked if wanted <= c.skills]

    def skill_gap_summary(self):
        n = len(self.ranked) or 1
        miss, have = {}, {}
        for c in self.ranked:
            for k in c.result["missing_required"]: miss[k] = miss.get(k, 0) + 1
            for k in c.result["matched"]: have[k] = have.get(k, 0) + 1
        return dict(total_candidates=len(self.ranked), required=self.jd.required, preferred=self.jd.preferred,
                    pct_missing_each_required={k: round(100 * miss.get(k, 0) / n) for k in self.jd.required},
                    most_common_matched=sorted(have, key=have.get, reverse=True)[:8])

    def draft_email(self, candidate_id, kind="invite"):
        c = self.by_id.get(candidate_id.upper())
        if not c: return {"error": "Unknown candidate"}
        who = "there" if self.anonymise else c.name.split()[0]
        r = c.result; top = ", ".join(r["matched"][:3]) or "your background"
        if kind == "reject":
            body = (f"Hi {who},\n\nThank you for applying. After careful review we won't be moving forward at this time. "
                    f"We'd encourage you to keep building experience in {', '.join(r['missing_required'][:2]) or 'the areas in the job description'} and to apply again.\n\nBest regards,\nRecruitment Team")
        else:
            body = (f"Hi {who},\n\nThanks for applying. Your experience with {top} stands out and we'd love to invite you to an interview. "
                    f"Please share your availability this week.\n\nBest regards,\nRecruitment Team")
        return dict(to="[hidden - anonymised mode]" if self.anonymise else c.email, subject="Your application update" if kind == "reject" else "Interview invitation", body=body)

    def recommend(self):
        if not self.ranked: return {"error": "No candidates"}
        best = self.ranked[0]; d = self._summary(best); r = best.result
        d["strengths"] = r["matched"]; d["concerns"] = [x for x in r["reasons"] if x.startswith(("Missing", "Experience")) and ("below" in x or "Missing" in x)]
        if len(self.ranked) > 1:
            d["runner_up"] = self._summary(self.ranked[1])
        return d

    def interview_questions(self, candidate_id):
        c = self.by_id.get(candidate_id.upper())
        if not c: return {"error": "Unknown candidate"}
        r = c.result; qs = []
        for k in r["missing_required"][:3]: qs.append(f"{k} is required for this role but not on the resume. Have you used it, and how quickly could you ramp up?")
        for k in r["matched"][:3]: qs.append(f"Describe a project where you used {k}. What was your exact contribution and what trade-offs did you make?")
        if r["years"] < self.jd.min_years: qs.append("The role expects more experience than your resume shows. Which project best proves you can handle the responsibility?")
        qs.append("Tell us about a time you debugged a hard production or project issue. How did you approach it?")
        return {"candidate": self.label(c), "questions": qs}

    def run(self, name, args):
        fn = getattr(self, name, None)
        if name.startswith("_") or not callable(fn) or name == "run": return {"error": f"unknown tool {name}"}
        try: return fn(**args)
        except Exception as e: return {"error": str(e)}

TOOLS = [
    {"name": "shortlist", "description": "Get the top-ranked candidates with scores and matched/missing skills.",
     "input_schema": {"type": "object", "properties": {"top_n": {"type": "integer"}, "min_score": {"type": "number"}}}},
    {"name": "get_candidate", "description": "Detailed explanation, score breakdown and skills for one candidate (e.g. C3).",
     "input_schema": {"type": "object", "properties": {"candidate_id": {"type": "string"}}, "required": ["candidate_id"]}},
    {"name": "compare", "description": "Compare several candidates side by side.",
     "input_schema": {"type": "object", "properties": {"candidate_ids": {"type": "array", "items": {"type": "string"}}}, "required": ["candidate_ids"]}},
    {"name": "find_by_skill", "description": "Find candidates having a given skill (or several, comma separated).",
     "input_schema": {"type": "object", "properties": {"skill": {"type": "string"}}, "required": ["skill"]}},
    {"name": "skill_gap_summary", "description": "Pool-level skill gap analysis against the job description.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "recommend", "description": "Recommend which candidate to hire/interview first, with strengths and concerns.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "interview_questions", "description": "Generate tailored interview questions for a candidate based on strengths and gaps.",
     "input_schema": {"type": "object", "properties": {"candidate_id": {"type": "string"}}, "required": ["candidate_id"]}},
    {"name": "draft_email", "description": "Draft an invite or rejection email for a candidate.",
     "input_schema": {"type": "object", "properties": {"candidate_id": {"type": "string"}, "kind": {"type": "string", "enum": ["invite", "reject"]}}, "required": ["candidate_id"]}},
]

SYSTEM = ("You are Resume Screening Copilot, an agentic recruiting assistant. Use the tools to ground every answer in the screening data; "
          "never invent candidate facts. Give clear reasons, mention skill gaps, and be fair: judge only job-relevant evidence, never protected "
          "characteristics. If candidates are anonymised, refer to them by ID only. Humans make the final hiring decision. Be concise.")

def llm_available(api_key=None):
    return bool(api_key or os.getenv("ANTHROPIC_API_KEY"))

def run_llm_agent(state, history, api_key=None, model=None, max_steps=6):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
    model = model or os.getenv("COPILOT_MODEL", "claude-sonnet-5-5")
    ctx = f"\nJob requirements: required={state.jd.required}, preferred={state.jd.preferred}, min_years={state.jd.min_years}. Candidates: {len(state.ranked)}. Anonymised: {state.anonymise}."
    msgs, trace = [dict(m) for m in history], []
    for _ in range(max_steps):
        resp = client.messages.create(model=model, max_tokens=1200, system=SYSTEM + ctx, tools=TOOLS, messages=msgs)
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text"), trace
        msgs.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = state.run(b.name, b.input); trace.append((b.name, b.input))
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out)})
        msgs.append({"role": "user", "content": results})
    return "I hit my step limit; please narrow the question.", trace

# ---------- offline copilot (no API key needed): intent routing over the same tools + built-in knowledge ----------
CONCEPTS = [
 (r"skill[- ]?gap", "A **skill gap** is the difference between the skills a job requires and the skills a candidate actually has. "
   "For example, if the JD needs Docker and a resume never mentions it, Docker is that candidate's skill gap. Recruiters use gaps to decide who needs training, who to reject, and what to ask in interviews."),
 (r"score|scoring|calculat|formula|weight", "The **match score (0-100)** is a transparent formula: **skills** (required skills count double, preferred skills count once) + "
   "**semantic similarity** (how close the resume wording is to the JD, using TF-IDF) + **experience** (years vs the minimum asked). Default weights are 55% / 20% / 25% and you can change them in the sidebar."),
 (r"bias|anonymi|anonym|fair|blind", "**Bias-aware mode** hides names, emails, phone numbers, links and gendered words (he/she/Mr/Ms) before scoring, and shows candidates as C1, C2... "
   "so shortlisting depends on skills and experience, not identity. C1 means upload order, not rank. After shortlisting you can reveal identity in the Candidate detail tab."),
 (r"verdict|strong match|potential|weak", "**Verdict** is a label from the score: 70+ = Strong match, 50-69 = Potential, below 50 = Weak match."),
 (r"semantic|similarity|tf-?idf", "**Semantic %** measures how similar the resume's overall wording is to the job description (TF-IDF cosine similarity). It catches relevant context that exact skill keywords can miss."),
 (r"experience|years", "**Experience** is estimated from work date ranges (like 2021-Present) and phrases like '5 years'. Education dates are ignored. Internships without dates are noted but not counted."),
 (r"agent|agentic|copilot|tool|what are you|who are you", "I am the **Resume Screening Copilot**, an agentic assistant. Instead of just chatting, I choose and run tools "
   "(shortlist, get candidate, compare, find by skill, skill gaps, recommend, interview questions, draft email) on the real screening data, so my answers are grounded in facts. The 'Agent steps' box shows which tools I called."),
 (r"parse|parsing|pdf|docx", "Resumes are parsed from **PDF / DOCX / TXT** into plain text, then I extract skills, years of experience, education and contact details."),
]

HELP = ("I can help with:\n- **Ranking:** 'top 3', 'who is best', 'who should I interview first?'\n- **One candidate:** 'why C1?', 'strengths of C2'\n"
        "- **Compare:** 'compare C1 and C2'\n- **Skills:** 'who knows Docker?', 'skill gaps'\n- **Actions:** 'interview questions for C1', 'draft invite for C1', 'draft rejection for C2'\n"
        "- **Concepts:** 'what is skill gap?', 'how is score calculated?', 'what is bias mode?'")

def _fmt(rows):
    return "\n".join(f"- **{r['candidate']}** · score {r['score']} ({r['verdict']}) · {r['years']:g} yrs · matched: {', '.join(r['matched_skills']) or '-'} · missing: {', '.join(r['missing_required']) or 'none'}" for r in rows)

def _find_ids(state, q):
    ids = [f"C{a or b}" for a, b in re.findall(r"\bc\s?(\d+)\b|candidate\s*#?\s*(\d+)", q)]
    if not state.anonymise:
        for c in state.ranked:
            if any(len(p) > 2 and p.lower() in q for p in c.name.split()): ids.append(c.cid)
    seen = []
    for i in ids:
        if i in state.by_id and i not in seen: seen.append(i)
    return seen

def run_offline_agent(state, question):
    q, trace = question.lower().strip(), []
    def call(n, **a): trace.append((n, a)); return state.run(n, a)
    ids = _find_ids(state, q)
    if not ids and re.search(r"\b(top|first|number one|#1)\s+(candidate|one|resume)|rank(ed)?\s*(1|one)\b", q) and state.ranked: ids = [state.ranked[0].cid]
    if not ids and state.last_id and re.search(r"\b(him|her|them|his|this candidate|that candidate|the candidate|same (one|candidate|person))\b", q): ids = [state.last_id]
    if re.fullmatch(r"(hi|hello|hey|help|\?|thanks|thank you|ok|okay)[\s!.]*", q) or re.search(r"what can you do|how to use|help me", q):
        return ("Hi! I'm your screening copilot. " if not re.search("thank", q) else "You're welcome! ") + HELP, trace
    if re.search(r"email|draft|invite|reject|mail", q):
        cid = ids[0] if ids else state.ranked[0].cid
        e = call("draft_email", candidate_id=cid, kind="reject" if "reject" in q else "invite")
        return f"Draft for **{cid}**\n\n**Subject:** {e['subject']}\n\n{e['body']}", trace
    if re.search(r"interview|question", q) and not re.search(r"first|who should", q):
        cid = ids[0] if ids else state.ranked[0].cid
        d = call("interview_questions", candidate_id=cid)
        return f"Interview questions for **{d['candidate']}**:\n" + "\n".join(f"{i+1}. {x}" for i, x in enumerate(d["questions"])), trace
    if "compare" in q or "difference" in q or "vs" in q.split():
        use = ids if len(ids) >= 2 else [c.cid for c in state.ranked[:2]]
        rows = call("compare", candidate_ids=use)
        return "**Comparison**\n" + _fmt(rows) + f"\n\nVerdict: **{rows[0]['candidate']}** leads with {rows[0]['score']} vs {rows[1]['score']}." if len(rows) > 1 and rows[0].get("score", 0) >= rows[1].get("score", 0) else "**Comparison**\n" + _fmt(rows), trace
    if not ids:
        for pat, text in CONCEPTS:
            if re.search(r"\b(what|explain|define|meaning|how|why)\b", q) and re.search(pat, q) and not re.search(r"\b(who|which)\b", q):
                extra = ""
                if re.search(r"skill[- ]?gap", pat):
                    g = call("skill_gap_summary"); miss = {k: v for k, v in g["pct_missing_each_required"].items() if v}
                    extra = ("\n\n**In your current screening:** " + ", ".join(f"{k} missing in {v}% of candidates" for k, v in sorted(miss.items(), key=lambda x: -x[1]))) if miss else "\n\n**In your current screening:** no required-skill gaps, all candidates have every required skill."
                return text + extra, trace
    if re.search(r"recommend|who should|should i (hire|select|interview)|hire|select|suitable|right fit|best|strongest|winner", q) and not ids:
        d = call("recommend")
        if "error" in d: return d["error"], trace
        out = f"**Recommendation: {d['candidate']}** (score {d['score']}, {d['verdict']}).\n\nStrengths: {', '.join(d['strengths']) or '-'}."
        if d["concerns"]: out += "\n\nConcerns:\n" + "\n".join("- " + x for x in d["concerns"])
        if "runner_up" in d: out += f"\n\nRunner-up: **{d['runner_up']['candidate']}** ({d['runner_up']['score']}). Final decision should be made by a human after interviews."
        return out, trace
    if re.search(r"gap|missing|lack|weak(ness)?\b", q) and not ids:
        g = call("skill_gap_summary")
        lines = [f"- {k}: missing in {v}% of candidates" for k, v in sorted(g["pct_missing_each_required"].items(), key=lambda x: -x[1])]
        note = "" if any(g["pct_missing_each_required"].values()) else "\n\nNo gaps: every candidate has all required skills."
        return f"**Skill-gap summary** ({g['total_candidates']} candidates)\n" + "\n".join(lines) + note + f"\n\nMost common matched skills: {', '.join(g['most_common_matched'])}", trace
    if ids:
        d = call("get_candidate", candidate_id=ids[0])
        if "error" in d: return d["error"], trace
        return (f"**{d['candidate']}**: rank #{d['rank']}, score {d['score']} ({d['verdict']})\n\n**Why:**\n" + "\n".join("- " + r for r in d["reasons"]) +
                f"\n\n**Strengths:** {', '.join(d['matched_skills']) or '-'}\n**Gaps:** {', '.join(d['missing_required']) or 'none'}\n"
                f"**Score breakdown:** skills {d['score_breakdown']['skills']}%, semantic {d['score_breakdown']['semantic']}%, experience {d['score_breakdown']['experience']}%"), trace
    sk = extract_skills(question)
    if sk and re.search(r"who|has|have|know|with|experience|find|anyone|list", q):
        rows = call("find_by_skill", skill=", ".join(sk))
        return (f"Candidates with {', '.join(sorted(sk))}:\n" + _fmt(rows)) if rows else f"No candidate has all of: {', '.join(sorted(sk))}.", trace
    m = re.search(r"top\s*(\d+)|(\d+)\s*best", q)
    if re.search(r"top|shortlist|rank|list|all candidates|show", q):
        n = int((m.group(1) or m.group(2))) if m else 5
        return f"Top {n} candidates:\n" + _fmt(call("shortlist", top_n=n)), trace
    return "I didn't fully get that, but here is what I can do.\n\n" + HELP, trace
