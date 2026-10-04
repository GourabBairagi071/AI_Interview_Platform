"""
Question Bank Data Builder for AI Interview Platform.
Generates 5,000+ unique, technically rigorous interview questions across 47 technologies.
"""

def slugify(text: str) -> str:
    cleaned = text.lower().replace("+", "-plus").replace(".", "-").replace("/", "-")
    chars = [c if c.isalnum() or c == "-" else "-" for c in cleaned]
    slug = "".join(chars)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")

# Domain Roles mapping
TECH_ROLES = {
    "DSA": "Software Engineer",
    "Algorithms": "Software Engineer",
    "DBMS": "Database Administrator",
    "SQL": "Data Analyst / Database Engineer",
    "OS": "Systems Engineer",
    "Computer Networks": "Network Engineer",
    "OOP": "Software Engineer",
    "C": "Embedded Systems Engineer",
    "C++": "Systems Software Engineer",
    "Java": "Backend Java Engineer",
    "Python": "Python Backend / Data Engineer",
    "JavaScript": "Frontend / Fullstack Developer",
    "TypeScript": "Fullstack TypeScript Engineer",
    "Kotlin": "Android / Mobile Engineer",
    "React": "Frontend React Engineer",
    "Next.js": "Fullstack Next.js Engineer",
    "Node.js": "Backend Node.js Engineer",
    "Express": "Backend API Developer",
    "MongoDB": "NoSQL Database Engineer",
    "PostgreSQL": "Relational Database Engineer",
    "Statistics": "Data Scientist",
    "Data Science": "Data Scientist",
    "Machine Learning": "Machine Learning Engineer",
    "Deep Learning": "Deep Learning Researcher",
    "NLP": "NLP Engineer",
    "Computer Vision": "Computer Vision Engineer",
    "AI": "AI Research Engineer",
    "GenAI": "Generative AI Engineer",
    "LLMs": "LLM Engineer",
    "RAG": "AI Systems Architect",
    "Vector Databases": "AI Infrastructure Engineer",
    "LangChain": "LLM Application Developer",
    "Data Engineering": "Data Engineer",
    "Spark": "Big Data Engineer",
    "Kafka": "Distributed Streaming Engineer",
    "Cloud": "Cloud Solutions Architect",
    "AWS": "AWS Cloud Architect",
    "GCP": "Google Cloud Architect",
    "Azure": "Azure Cloud Engineer",
    "Docker": "DevOps / Platform Engineer",
    "Kubernetes": "Site Reliability Engineer",
    "DevOps": "DevOps Engineer",
    "Linux": "Linux Systems Administrator",
    "Git": "Software Engineer",
    "System Design": "System Architect",
    "Distributed Systems": "Distributed Systems Engineer",
    "Cybersecurity": "Cybersecurity Specialist",
}
