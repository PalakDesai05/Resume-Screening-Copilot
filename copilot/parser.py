"""Resume parsing (PDF/DOCX/TXT), experience extraction, anonymisation."""
import io, re, datetime
from dataclasses import dataclass, field
from .skills import extract_skills

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PH = re.compile(r"(?<!\d)\+?\d[\d\s\-()]{8,}\d(?!\d)")
class _Phone:
    """Phone matcher requiring >=10 digits (avoids matching year ranges)."""
    def _ok(self, m): return len(re.sub(r"\D", "", m.group(0))) >= 10
    def search(self, t): return next((m for m in _PH.finditer(t) if self._ok(m)), None)
    def sub(self, r, t): return _PH.sub(lambda m: r if self._ok(m) else m.group(0), t)
PHONE = _Phone()
URL = re.compile(r"(?:https?://|www\.|linkedin\.com|github\.com)\S+", re.I)
EDU = [("phd", r"ph\.?d|doctorate"), ("masters", r"m\.?tech|m\.?sc|m\.?e\b|mba|master"), ("bachelors", r"b\.?tech|b\.?e\b|b\.?sc|bca|bachelor|b\.?com")]

@dataclass
class Candidate:
    cid: str
    filename: str
    raw_text: str
    name: str
    email: str
    phone: str
    skills: set
    years: float
    education: str
    anon_text: str = ""
    internship: bool = False
    result: dict = field(default_factory=dict)

def read_file(filename: str, data: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    if ext == "docx":
        import docx
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    return data.decode("utf-8", errors="ignore")

def guess_name(text: str, filename: str) -> str:
    for line in text.splitlines():
        l = line.strip()
        if l and len(l.split()) <= 4 and not EMAIL.search(l) and not re.search(r"\d", l) and not l.lower().startswith(("resume", "curriculum")):
            return l.title()
    return re.sub(r"[_\-.]+", " ", filename.rsplit(".", 1)[0]).title()

EDU_LINE = re.compile(r"college|university|school|institute|vidyalay|b\.?tech|m\.?tech|b\.?e\b|b\.?sc|m\.?sc|cgpa|gpa|hsc|ssc|bachelor|master|diploma|degree", re.I)

def work_lines(text: str) -> str:
    """Drop the EDUCATION section and education-looking lines so study dates are not counted as work experience."""
    keep, in_edu = [], False
    for line in text.splitlines():
        s = line.strip()
        if re.fullmatch(r"(education|academics|academic (background|qualifications?))\s*:?", s, re.I): in_edu = True; continue
        if in_edu and s.isupper() and 3 < len(s) < 40: in_edu = False
        if not in_edu and not EDU_LINE.search(s): keep.append(line)
    return "\n".join(keep)

def years_of_experience(text: str) -> float:
    now = datetime.date.today().year
    text = work_lines(text)
    stated = [int(m) for m in re.findall(r"(\d{1,2})\+?\s*(?:years|yrs)", text, re.I) if int(m) <= 40]
    spans = []
    for a, b in re.findall(r"((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current|now)", text, re.I):
        s = int(a); e = now if b.isalpha() else min(int(b), now)
        if 0 <= e - s <= 40: spans.append((s, e))
    spans.sort(); total, cur = 0, None
    for s, e in spans:
        if cur is None: cur = [s, e]
        elif s <= cur[1]: cur[1] = max(cur[1], e)
        else: total += cur[1] - cur[0]; cur = [s, e]
    if cur: total += cur[1] - cur[0]
    return float(max([total] + stated[:3])) if (spans or stated) else 0.0

def education_level(text: str) -> str:
    for label, pat in EDU:
        if re.search(r"\b(?:%s)" % pat, text, re.I): return label
    return "unspecified"

def anonymise(text: str, name: str) -> str:
    t = EMAIL.sub("[EMAIL]", text); t = URL.sub("[LINK]", t); t = PHONE.sub("[PHONE]", t)
    for part in name.split():
        if len(part) > 2: t = re.sub(re.escape(part), "[NAME]", t, flags=re.I)
    t = re.sub(r"\b(he|she|him|her|his|hers|mr|mrs|ms)\b\.?", "[X]", t, flags=re.I)
    return t

def parse_resume(idx: int, filename: str, data: bytes) -> Candidate:
    text = read_file(filename, data)
    name = guess_name(text, filename)
    em = EMAIL.search(text); ph = PHONE.search(text)
    c = Candidate(f"C{idx}", filename, text, name, em.group(0) if em else "", ph.group(0).strip() if ph else "",
                  extract_skills(text), years_of_experience(text), education_level(text))
    c.anon_text = anonymise(text, name)
    c.internship = bool(re.search(r"intern", text, re.I))
    return c
