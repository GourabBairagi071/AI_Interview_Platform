import re

CANONICAL_SKILLS_MAP: dict[str, tuple[str, str]] = {
    # Programming Languages -> (Canonical Name, Category)
    "python": ("Python", "Programming Languages"),
    "python 3": ("Python", "Programming Languages"),
    "python programming": ("Python", "Programming Languages"),
    "python language": ("Python", "Programming Languages"),
    "javascript": ("JavaScript", "Programming Languages"),
    "js": ("JavaScript", "Programming Languages"),
    "es6": ("JavaScript", "Programming Languages"),
    "typescript": ("TypeScript", "Programming Languages"),
    "ts": ("TypeScript", "Programming Languages"),
    "java": ("Java", "Programming Languages"),
    "core java": ("Java", "Programming Languages"),
    "c++": ("C++", "Programming Languages"),
    "cpp": ("C++", "Programming Languages"),
    "c": ("C", "Programming Languages"),
    "c#": ("C#", "Programming Languages"),
    "csharp": ("C#", "Programming Languages"),
    "golang": ("Go", "Programming Languages"),
    "go": ("Go", "Programming Languages"),
    "rust": ("Rust", "Programming Languages"),
    "php": ("PHP", "Programming Languages"),
    "ruby": ("Ruby", "Programming Languages"),

    # Backend Frameworks
    "fastapi": ("FastAPI", "Backend Development"),
    "fast api": ("FastAPI", "Backend Development"),
    "flask": ("Flask", "Backend Development"),
    "django": ("Django", "Backend Development"),
    "express": ("Express.js", "Backend Development"),
    "expressjs": ("Express.js", "Backend Development"),
    "express.js": ("Express.js", "Backend Development"),
    "node": ("Node.js", "Backend Development"),
    "nodejs": ("Node.js", "Backend Development"),
    "node.js": ("Node.js", "Backend Development"),
    "spring": ("Spring Boot", "Backend Development"),
    "spring boot": ("Spring Boot", "Backend Development"),
    "nest": ("NestJS", "Backend Development"),
    "nestjs": ("NestJS", "Backend Development"),

    # Frontend Frameworks
    "react": ("React", "Frontend Development"),
    "reactjs": ("React", "Frontend Development"),
    "react.js": ("React", "Frontend Development"),
    "next": ("Next.js", "Frontend Development"),
    "nextjs": ("Next.js", "Frontend Development"),
    "next.js": ("Next.js", "Frontend Development"),
    "vue": ("Vue.js", "Frontend Development"),
    "vuejs": ("Vue.js", "Frontend Development"),
    "vue.js": ("Vue.js", "Frontend Development"),
    "angular": ("Angular", "Frontend Development"),
    "html": ("HTML & CSS", "Frontend Development"),
    "css": ("HTML & CSS", "Frontend Development"),
    "html5": ("HTML & CSS", "Frontend Development"),
    "css3": ("HTML & CSS", "Frontend Development"),
    "tailwind": ("Tailwind CSS", "Frontend Development"),
    "tailwindcss": ("Tailwind CSS", "Frontend Development"),

    # Databases & Storage
    "sql": ("SQL", "Databases"),
    "relational database": ("SQL", "Databases"),
    "rdbms": ("SQL", "Databases"),
    "postgresql": ("PostgreSQL", "Databases"),
    "postgres": ("PostgreSQL", "Databases"),
    "mysql": ("MySQL", "Databases"),
    "sqlite": ("SQLite", "Databases"),
    "mongodb": ("MongoDB", "Databases"),
    "nosql": ("MongoDB", "Databases"),
    "redis": ("Redis", "Databases"),
    "caching": ("Redis", "Databases"),
    "elasticsearch": ("Elasticsearch", "Databases"),

    # Data Structures & Algorithms
    "dsa": ("Data Structures & Algorithms", "Algorithms"),
    "data structures": ("Data Structures & Algorithms", "Algorithms"),
    "algorithms": ("Data Structures & Algorithms", "Algorithms"),
    "data structures and algorithms": ("Data Structures & Algorithms", "Algorithms"),
    "arrays": ("Arrays & Strings", "Algorithms"),
    "array": ("Arrays & Strings", "Algorithms"),
    "strings": ("Arrays & Strings", "Algorithms"),
    "string": ("Arrays & Strings", "Algorithms"),
    "trees": ("Trees & Binary Search Trees", "Algorithms"),
    "tree": ("Trees & Binary Search Trees", "Algorithms"),
    "binary tree": ("Trees & Binary Search Trees", "Algorithms"),
    "binary search tree": ("Trees & Binary Search Trees", "Algorithms"),
    "bst": ("Trees & Binary Search Trees", "Algorithms"),
    "graphs": ("Graphs", "Algorithms"),
    "graph": ("Graphs", "Algorithms"),
    "graph algorithms": ("Graphs", "Algorithms"),
    "dynamic programming": ("Dynamic Programming", "Algorithms"),
    "dp": ("Dynamic Programming", "Algorithms"),
    "sorting": ("Sorting & Searching", "Algorithms"),
    "searching": ("Sorting & Searching", "Algorithms"),
    "binary search": ("Sorting & Searching", "Algorithms"),
    "recursion": ("Recursion & Backtracking", "Algorithms"),
    "backtracking": ("Recursion & Backtracking", "Algorithms"),
    "linked list": ("Linked Lists", "Algorithms"),
    "linked lists": ("Linked Lists", "Algorithms"),
    "stack": ("Stacks & Queues", "Algorithms"),
    "queue": ("Stacks & Queues", "Algorithms"),
    "stacks & queues": ("Stacks & Queues", "Algorithms"),
    "heaps": ("Heaps & Priority Queues", "Algorithms"),
    "heap": ("Heaps & Priority Queues", "Algorithms"),
    "greedy": ("Greedy Algorithms", "Algorithms"),

    # Architecture & Infrastructure
    "system design": ("System Design", "System Architecture"),
    "distributed systems": ("System Design", "System Architecture"),
    "scalability": ("System Design", "System Architecture"),
    "rest": ("REST APIs", "System Architecture"),
    "rest api": ("REST APIs", "System Architecture"),
    "restful api": ("REST APIs", "System Architecture"),
    "rest apis": ("REST APIs", "System Architecture"),
    "graphql": ("GraphQL", "System Architecture"),
    "microservices": ("Microservices", "System Architecture"),
    "docker": ("Docker", "DevOps & Cloud"),
    "containerization": ("Docker", "DevOps & Cloud"),
    "containers": ("Docker", "DevOps & Cloud"),
    "kubernetes": ("Kubernetes", "DevOps & Cloud"),
    "k8s": ("Kubernetes", "DevOps & Cloud"),
    "ci/cd": ("CI/CD", "DevOps & Cloud"),
    "cicd": ("CI/CD", "DevOps & Cloud"),
    "git": ("Git", "DevOps & Cloud"),
    "github": ("Git", "DevOps & Cloud"),
    "version control": ("Git", "DevOps & Cloud"),
    "aws": ("Cloud Computing (AWS)", "DevOps & Cloud"),
    "cloud": ("Cloud Computing (AWS)", "DevOps & Cloud"),

    # AI & Machine Learning
    "machine learning": ("Machine Learning", "AI & Machine Learning"),
    "ml": ("Machine Learning", "AI & Machine Learning"),
    "deep learning": ("Deep Learning", "AI & Machine Learning"),
    "dl": ("Deep Learning", "AI & Machine Learning"),
    "nlp": ("Natural Language Processing", "AI & Machine Learning"),
    "natural language processing": ("Natural Language Processing", "AI & Machine Learning"),
    "llm": ("Generative AI & LLMs", "AI & Machine Learning"),
    "llms": ("Generative AI & LLMs", "AI & Machine Learning"),
    "generative ai": ("Generative AI & LLMs", "AI & Machine Learning"),
    "rag": ("RAG & Vector Search", "AI & Machine Learning"),
}


def normalize_skill_name(raw_name: str) -> tuple[str, str]:
    """
    Normalizes arbitrary skill strings, topic labels, or resume keywords
    into a canonical skill name and category.
    Returns: (canonical_name, category)
    """
    if not raw_name or not isinstance(raw_name, str):
        return ("General Engineering", "General")

    cleaned = raw_name.strip().lower()
    cleaned = re.sub(r"[\-_/]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Exact match in canonical map
    if cleaned in CANONICAL_SKILLS_MAP:
        return CANONICAL_SKILLS_MAP[cleaned]

    # Partial / substring lookup
    for key, (canonical, category) in CANONICAL_SKILLS_MAP.items():
        if len(key) >= 3 and (key == cleaned or f" {key} " in f" {cleaned} "):
            return (canonical, category)

    # Fallback to Title Cased representation
    title_cased = raw_name.strip().title()
    return (title_cased, "Technical")
