"""Generates sample JD + resumes (DOCX/TXT/PDF-free) into sample_data/."""
import os, docx
os.makedirs("sample_data/resumes", exist_ok=True)
open("sample_data/sample_jd.txt", "w").write("""AI Engineer (Generative AI)
We need an AI Engineer with 3+ years of experience building LLM applications.
Required: Python, LLMs, RAG, FastAPI, Docker, SQL, Git, REST APIs.
Nice to have: LangChain, AWS, Kubernetes, Vector Databases (FAISS/Pinecone), MLOps.
""")
R = {
"Aarav_Sharma.docx": """Aarav Sharma
aarav.sharma@mail.com | +91 98765 43210 | github.com/aarav
Summary: AI engineer with 5 years of experience. He builds production LLM and RAG systems.
Experience
Senior AI Engineer, TechNova 2021 - Present: Python, FastAPI, LangChain, FAISS, Docker, AWS, REST APIs, SQL, Git. Built RAG chatbot.
ML Engineer, DataWorks 2019 - 2021: Machine Learning, PyTorch, MLOps, Kubernetes.
Education: M.Tech Computer Science""",
"Priya_Nair.docx": """Priya Nair
priya.nair@mail.com | 9123456780
Data analyst with 4 years experience. She works with SQL, Excel, Power BI, Tableau and Python (Pandas).
Data Analyst, RetailCo 2022 - 2025: dashboards, Data Analysis, SQL, Python, Statistics.
B.Sc Statistics""",
"Rohan_Mehta.txt": """Rohan Mehta
rohan.m@mail.com | +91 90000 11111
Full stack developer, 3 years of experience. JavaScript, React, Node.js, Docker, Git, REST APIs, SQL.
Developer, WebSoft 2022 - 2025. Recently learning LLMs and prompt engineering.
B.E. Computer Engineering""",
"Sneha_Iyer.txt": """Sneha Iyer
sneha.iyer@mail.com | 8888877777
Generative AI engineer with 3 years of experience. Python, LLMs, RAG, FastAPI, Docker, Git, SQL, REST APIs, Pinecone, GCP.
AI Engineer, Cognito Labs 2023 - Present. Built agentic workflows with LangGraph and Claude.
M.Sc Data Science""",
"Karan_Verma.txt": """Karan Verma
karan.v@mail.com | 7777788888
Fresher. B.Tech graduate, internship 2025 - 2026 in testing. Java, Selenium, Excel, Communication.""",
}
for n, t in R.items():
    if n.endswith(".docx"):
        d = docx.Document(); [d.add_paragraph(l) for l in t.split("\n")]; d.save(f"sample_data/resumes/{n}")
    else: open(f"sample_data/resumes/{n}", "w").write(t)
