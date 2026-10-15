"""Skill taxonomy + extraction (canonical skill -> aliases)."""
import re

TAXONOMY = {
    "Python": ["python"], "Java": ["java"], "JavaScript": ["javascript", "js", "node.js", "nodejs"],
    "TypeScript": ["typescript"], "C++": ["c++"], "C#": ["c#"], "Go": ["golang"], "SQL": ["sql", "mysql", "postgresql", "postgres"],
    "NoSQL": ["mongodb", "cassandra", "dynamodb", "nosql"], "React": ["react", "react.js", "reactjs"],
    "Angular": ["angular"], "Django": ["django"], "Flask": ["flask"], "FastAPI": ["fastapi"], "Spring Boot": ["spring boot", "spring"],
    "REST APIs": ["rest api", "rest apis", "restful"], "Microservices": ["microservices"], "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"], "AWS": ["aws", "amazon web services"], "Azure": ["azure"], "GCP": ["gcp", "google cloud"],
    "CI/CD": ["ci/cd", "jenkins", "github actions", "gitlab ci"], "Git": ["git", "github", "gitlab"], "Linux": ["linux"],
    "Machine Learning": ["machine learning", "ml", "xgboost", "k-means"], "Deep Learning": ["deep learning", "neural networks", "cnn", "lstm", "dl"],
    "NLP": ["nlp", "natural language processing", "bert", "transformers"], "Computer Vision": ["computer vision", "opencv"],
    "TensorFlow": ["tensorflow"], "PyTorch": ["pytorch"], "scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"], "NumPy": ["numpy"], "Generative AI": ["generative ai", "genai", "gen ai"],
    "LLMs": ["llm", "llms", "large language models", "gpt", "claude"], "RAG": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    "LangChain": ["langchain", "langgraph"], "Prompt Engineering": ["prompt engineering"], "Vector Databases": ["faiss", "pinecone", "chromadb", "vector database", "vector databases"],
    "Data Analysis": ["data analysis", "data analytics"], "Power BI": ["power bi", "powerbi"], "Tableau": ["tableau"], "Excel": ["excel"],
    "Spark": ["spark", "pyspark"], "Hadoop": ["hadoop"], "Airflow": ["airflow"], "ETL": ["etl"], "Kafka": ["kafka"],
    "Statistics": ["statistics", "statistical modeling"], "MLOps": ["mlops"], "Agile": ["agile", "scrum"], "Jira": ["jira"],
    "HTML/CSS": ["html", "css", "html5", "css3"], "Selenium": ["selenium"], "Testing": ["unit testing", "pytest", "junit", "test automation"],
    "Kotlin": ["kotlin"], "Firebase": ["firebase"], "DSA": ["dsa", "data structures"], "OOP": ["oop", "object oriented"], "Communication": ["communication"], "Leadership": ["leadership", "team lead", "mentoring"], "Project Management": ["project management"],
    "Recruitment": ["recruitment", "talent acquisition", "sourcing"], "Cybersecurity": ["cybersecurity", "security"],
}

def _pat(alias):
    return re.compile(r"(?<![\w+#.])" + re.escape(alias) + r"(?![\w+#]|\.\w)", re.I)

_PATTERNS = {c: [_pat(a) for a in al + [c.lower()]] for c, al in TAXONOMY.items()}

_DISTINCT = {"Vector Databases": "faiss", "Vector Databases ": "pinecone", "LangChain": "langchain", "Kubernetes": "kubernetes", "TensorFlow": "tensorflow", "PyTorch": "pytorch", "FastAPI": "fastapi", "NoSQL": "mongodb"}
_DISTINCT = {k.strip(): v for k, v in _DISTINCT.items()}

def extract_skills(text: str) -> set:
    found = {c for c, pats in _PATTERNS.items() if any(p.search(text) for p in pats)}
    squashed = re.sub(r"\s+", "", text.lower())  # PDFs sometimes split words ("FAI SS")
    for canon, tok in _DISTINCT.items():
        if tok in squashed: found.add(canon)
    if found & {"LLMs", "RAG", "LangChain", "Prompt Engineering"}: found.add("Generative AI")
    return found

def canonical(name: str):
    """Map a free-text skill mention to canonical taxonomy name."""
    s = extract_skills(name)
    return next(iter(s)) if s else None
