"""Core engine: resume parsing, skill/experience extraction, anonymisation, scoring."""
import io, re
from datetime import date
from pypdf import PdfReader
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── Skill dictionary: "Canonical=alias1|alias2" (canonical name is always an alias) ──
_RAW = """Python=python3
Java=
JavaScript=ecmascript
TypeScript=
C++=cpp
C#=csharp
Golang=
Kotlin=
PHP=
Bash=shell scripting
SQL=
React=react.js|reactjs
Angular=angularjs
Vue=vue.js|vuejs
Node.js=nodejs|node js
Express.js=expressjs
Django=
Flask=
FastAPI=fast api
Spring Boot=springboot
HTML=html5
CSS=css3
Tailwind CSS=tailwind
REST APIs=rest api|restful|restful api|restful apis
GraphQL=
Machine Learning=ml
Deep Learning=neural networks|cnn|rnn|lstm
NLP=natural language processing
Computer Vision=opencv|image processing
PyTorch=torch
TensorFlow=keras
scikit-learn=sklearn|scikit learn
Pandas=
NumPy=
Data Analysis=data analytics
Data Visualization=data visualisation|matplotlib|seaborn|plotly
Power BI=powerbi
Tableau=
Excel=ms excel|microsoft excel
Statistics=statistical analysis
Feature Engineering=
LLMs=llm|large language model|large language models|gpt|chatgpt
RAG=retrieval augmented generation|retrieval-augmented generation
Prompt Engineering=prompt design|prompting
LangChain=langgraph
LlamaIndex=
Hugging Face=huggingface|transformers
Vector Databases=vector database|vector db|vector store|faiss|pinecone|chromadb|chroma|weaviate|milvus|pgvector|qdrant
OpenAI API=openai
Fine-tuning=finetuning|fine tuning|lora|qlora|peft
Generative AI=genai|gen ai|gen-ai
MySQL=
PostgreSQL=postgres
MongoDB=mongo
Redis=
Neo4j=
Docker=docker compose|dockerfile
Kubernetes=k8s
AWS=amazon web services|ec2|sagemaker
Azure=microsoft azure
GCP=google cloud|google cloud platform|vertex ai
CI/CD=cicd|continuous integration
Git=github|gitlab|version control
Linux=
Jenkins=
Terraform=
Apache Spark=pyspark|spark
Kafka=
Airflow=apache airflow
Streamlit=
Microservices=microservice
System Design=
Data Structures=dsa|algorithms
OOP=object oriented programming|object-oriented programming
Agile=scrum"""
SKILLS = {}
for _l in _RAW.splitlines():
    _k, _, _a = _l.partition("=")
    SKILLS[_k] = [_k.lower()] + [x for x in _a.split("|") if x]
_PAT = {k: re.compile(r"(?<![A-Za-z0-9+#.])(?:%s)(?![A-Za-z0-9])" % "|".join(map(re.escape, sorted(v, key=len, reverse=True))), re.I)
        for k, v in SKILLS.items()}


def extract_skills(text):
    """Skills found in text, in dictionary order."""
    return [k for k, p in _PAT.items() if p.search(text)]


# ── File reading ──
def read_file(name, data):
    ext = name.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    if ext == "docx":
        d = Document(io.BytesIO(data))
        cells = [c.text for t in d.tables for r in t.rows for c in r.cells]
        return "\n".join([p.text for p in d.paragraphs] + cells)
    return data.decode("utf-8", errors="ignore")


def guess_name(text, fallback):
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    ok = 1 < len(first.split()) <= 4 and not re.search(r"[\d@:/|,]", first)
    return first.title() if ok else re.sub(r"[_\-]+", " ", fallback.rsplit(".", 1)[0]).title()


def contacts(text):
    em = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    ph = re.search(r"\+?\d[\d\s().-]{8,}\d", text)
    return {"email": em.group() if em else "", "phone": ph.group().strip() if ph and len(re.sub(r"\D", "", ph.group())) >= 10 else ""}


# ── Experience (work date ranges only; education / projects are ignored) ──
MON = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
_D = r"(?:(%s)[a-z]*\.?,?\s+)?(\d{4})" % "|".join(MON)
_RANGE = re.compile(rf"{_D}\s*(?:-|–|—|to|till)\s*(?:{_D}|(present|current|now|ongoing|date))", re.I)
_EXP_H = re.compile(r"(work |professional |relevant |industry )?(experience|employment( history)?|work history|internships?)")
_OTH_H = re.compile(r"(education|academic (background|qualifications?)|qualifications?|(personal |academic |key )?projects?|(technical )?skills|certifications?|achievements|awards|publications|(professional )?summary|profile|objective|languages|interests|hobbies|references|contact)")
_EDU = re.compile(r"b\.?tech|\bb\.?e\b|bachelor|master|m\.?tech|\bmba\b|b\.?sc|m\.?sc|university|college|institute|school|cgpa|\bgpa\b|hsc|ssc|diploma|degree", re.I)


def experience(text):
    sec, iv, today = None, [], date.today()
    for ln in text.splitlines():
        h = re.sub(r"[^a-z ]", "", ln.lower()).strip()
        if h and len(h) < 35:
            if _EXP_H.fullmatch(h): sec = "exp"; continue
            if _OTH_H.fullmatch(h): sec = "other"; continue
        if sec in (None, "exp") and not _EDU.search(ln):
            for m in _RANGE.finditer(ln):
                sm, sy, em, ey, pres = m.groups()
                s = int(sy) * 12 + (MON[sm.lower()[:3]] if sm else 1)
                e = today.year * 12 + today.month if pres else int(ey) * 12 + (MON[em.lower()[:3]] if em else 12)
                if 0 <= e - s <= 600: iv.append((s, e))
    iv.sort(); tot, cur = 0, None
    for s, e in iv:  # merge overlaps so parallel jobs are not double counted
        if cur and s <= cur[1]: cur[1] = max(cur[1], e)
        else:
            if cur: tot += cur[1] - cur[0]
            cur = [s, e]
    if cur: tot += cur[1] - cur[0]
    said = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:\w+\s+){0,2}experience", text, re.I)]
    return round(max([tot / 12] + said), 1)


# ── Bias-aware anonymiser ──
_G = {"he": "they", "she": "they", "him": "them", "her": "them", "his": "their", "hers": "theirs", "himself": "themselves", "herself": "themselves"}


def anonymise(text, name=""):
    t = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL]", text)
    t = re.sub(r"(https?://\S+|www\.\S+|(?:linkedin|github)\.com/\S+)", "[LINK]", t, flags=re.I)
    t = re.sub(r"\+?\d[\d\s().-]{8,}\d", lambda m: "[PHONE]" if len(re.sub(r"\D", "", m.group())) >= 10 else m.group(), t)
    t = re.sub(r"(?im)^\W*(date of birth|dob|age|gender|sex|marital status|nationality)\b.*$", "", t)
    t = re.sub(r"(?i)\b(date of birth|dob)\s*[:\-]?\s*[\w ,/.-]{6,20}", "", t)
    for tok in {w for w in name.split() if len(w) > 2}:
        t = re.sub(rf"\b{re.escape(tok)}\b", "[NAME]", t, flags=re.I)
    t = re.sub(r"\b(Mr|Mrs|Ms|Miss)\.?\s", "", t)
    t = re.sub(r"\b(%s)\b" % "|".join(_G), lambda m: _G[m.group().lower()], t, flags=re.I)
    return re.sub(r"\b(they) (has|is|was|does)\b", lambda m: m.group(1) + " " + {"has": "have", "is": "are", "was": "were", "does": "do"}[m.group(2)], t)


def make_candidate(i, filename, data):
    text = read_file(filename, data)
    name = guess_name(text, filename)
    return {"id": f"C{i}", "file": filename, "name": name, "text": text, "anon": anonymise(text, name),
            "warn": "" if len(text.strip()) > 80 else "Little or no text found — scanned PDF? OCR needed."}


# ── Job description ──
def parse_job(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    has_h = bool(re.search(r"(?im)^\W*(required|preferred|nice to have|must have|good to have|bonus)", text))
    mode, req, pref = (None if has_h else "req"), [], []
    for l in lines:
        low = l.lower()
        if len(l) < 60:
            if re.match(r"\W*(preferred|nice to have|good to have|bonus)", low): mode = "pref"; continue
            if re.match(r"\W*(required|must have|requirements|qualifications|key skills|skills)", low): mode = "req"; continue
            if re.match(r"\W*(responsibilities|about|what you)", low): mode = None; continue
        if mode: (req if mode == "req" else pref).extend(extract_skills(l))
    req = [k for k in SKILLS if k in req]
    pref = [k for k in SKILLS if k in pref and k not in req]
    yrs = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", text, re.I)
    return {"title": lines[0][:80] if lines else "Job", "required": req, "preferred": pref,
            "min_years": float(yrs.group(1)) if yrs else 0.0, "text": text}


# ── Scoring ──
SEM_CAP = 0.40  # TF-IDF cosine rarely exceeds ~0.4 for a resume vs a JD, so 0.40 counts as 100%


def verdict(s):
    return "Strong match" if s >= 70 else "Potential" if s >= 50 else "Weak match"


def score_all(cands, job, w, bias=True):
    """Score candidates in place. w = {'skills','semantic','experience'} (any scale, normalised here)."""
    if not cands: return
    texts = [c["anon"] if bias else c["text"] for c in cands]
    try:
        sims = cosine_similarity(TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
                                 .fit_transform([job["text"]] + texts))[0, 1:]
    except ValueError:
        sims = [0.0] * len(cands)
    tw = sum(w.values()) or 1
    req, pref, den = job["required"], job["preferred"], 2 * len(job["required"]) + len(job["preferred"])
    for c, t, s in zip(cands, texts, sims):
        sk = set(extract_skills(t)); c["skills"] = sk
        c["req_hit"] = [k for k in req if k in sk]; c["req_miss"] = [k for k in req if k not in sk]
        c["pref_hit"] = [k for k in pref if k in sk]
        c["yrs"] = experience(t)
        parts = {"skills": (2 * len(c["req_hit"]) + len(c["pref_hit"])) / den if den else 0.0,
                 "semantic": min(1.0, float(s) / SEM_CAP),
                 "experience": min(1.0, c["yrs"] / job["min_years"]) if job["min_years"] else 1.0}
        c["max"] = {k: 100 * w[k] / tw for k in parts}
        c["pts"] = {k: c["max"][k] * v for k, v in parts.items()}
        c["score"] = round(sum(c["pts"].values()), 1)
        c["verdict"] = verdict(c["score"])
        c["why"] = f"{len(c['req_hit'])}/{len(req)} required skills, {len(c['pref_hit'])} bonus skills, {c['yrs']:g} years experience"
        if 0 < len(c["req_miss"]) <= 3: c["why"] += "; missing " + ", ".join(c["req_miss"])
