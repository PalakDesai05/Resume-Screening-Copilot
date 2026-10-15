"""JD parsing + transparent hybrid scoring (skills + semantic + experience) with explanations."""
import re
from dataclasses import dataclass, field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .skills import extract_skills

@dataclass
class JD:
    text: str
    required: list = field(default_factory=list)
    preferred: list = field(default_factory=list)
    min_years: float = 0.0

def parse_jd(text: str) -> JD:
    m = re.search(r"(nice to have|preferred|good to have|bonus|plus)", text, re.I)
    req_txt, pref_txt = (text[:m.start()], text[m.start():]) if m else (text, "")
    req = sorted(extract_skills(req_txt)); pref = sorted(extract_skills(pref_txt) - set(req))
    yrs = [int(x) for x in re.findall(r"(\d{1,2})\+?\s*(?:years|yrs)", text, re.I) if int(x) <= 30]
    return JD(text, req, pref, float(min(yrs)) if yrs else 0.0)

def score_all(jd: JD, cands: list, weights=(0.55, 0.20, 0.25)):
    ws, wm, we = weights
    texts = [jd.text] + [c.anon_text for c in cands]
    sem = [0.0] * len(cands)
    if cands:
        tf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit_transform(texts)
        sem = [min(1.0, float(s) / 0.45) for s in cosine_similarity(tf[0:1], tf[1:])[0]]
    tot_w = 2 * len(jd.required) + len(jd.preferred)
    for c, s in zip(cands, sem):
        req_hit = [k for k in jd.required if k in c.skills]; req_miss = [k for k in jd.required if k not in c.skills]
        pref_hit = [k for k in jd.preferred if k in c.skills]; pref_miss = [k for k in jd.preferred if k not in c.skills]
        sk = (2 * len(req_hit) + len(pref_hit)) / tot_w if tot_w else 0.0
        ex = min(1.0, c.years / jd.min_years) if jd.min_years else 1.0
        total = round(100 * (ws * sk + wm * s + we * ex), 1)
        verdict = "Strong match" if total >= 70 else "Potential" if total >= 50 else "Weak match"
        reasons = []
        if req_hit: reasons.append(f"Matches {len(req_hit)}/{len(jd.required)} required skills: {', '.join(req_hit)}.")
        if req_miss: reasons.append(f"Missing required skills: {', '.join(req_miss)}.")
        if pref_hit: reasons.append(f"Bonus skills present: {', '.join(pref_hit)}.")
        if jd.min_years:
            reasons.append(f"Experience ~{c.years:g} yrs vs {jd.min_years:g} yrs required" + (" (meets bar)." if c.years >= jd.min_years else " (below bar)."))
        if jd.min_years and c.years < jd.min_years and c.internship:
            reasons.append("Internship experience found (duration not stated, so not counted in years).")
        reasons.append(f"Overall content similarity to JD: {round(s*100)}%.")
        extras = sorted(c.skills - set(jd.required) - set(jd.preferred))
        c.result = dict(id=c.cid, score=total, verdict=verdict, skill_score=round(sk*100), semantic=round(s*100), exp_score=round(ex*100),
                        matched=req_hit + pref_hit, missing_required=req_miss, missing_preferred=pref_miss,
                        extra_skills=extras, reasons=reasons, years=c.years, education=c.education)
    return sorted(cands, key=lambda c: -c.result["score"])
