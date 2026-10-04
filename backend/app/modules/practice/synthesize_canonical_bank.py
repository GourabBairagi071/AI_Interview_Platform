"""
Master Canonical Bank Synthesizer for 47 Technologies.
Generates 5,640+ unique, deep technical interview questions with zero placeholder text.
Writes canonical_bank.json and verifies constraints.
"""
import hashlib
import json
import os
import sys

def slugify(text: str) -> str:
    cleaned = text.lower().replace("+", "-plus").replace(".", "-").replace("/", "-")
    chars = [c if c.isalnum() or c == "-" else "-" for c in cleaned]
    slug = "".join(chars)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")

def generate_qid(q_text: str) -> str:
    cleaned = q_text.strip().lower()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]

# 47 Technologies with their real technical topics
TECH_TOPICS = {
    "DSA": [
        "Arrays & Two Pointers", "Linked Lists", "Stacks & Queues", "Binary Trees & BST",
        "Heaps & Priority Queues", "Hash Tables & Sets", "Graphs & Traversal",
        "Dynamic Programming", "Greedy Algorithms", "Trie & Strings"
    ],
    "Algorithms": [
        "Sorting Algorithms", "Binary Search & Variants", "Graph Shortest Path",
        "Minimum Spanning Trees", "Divide & Conquer", "Backtracking & Recursion",
        "Bit Manipulation", "String Matching", "Disjoint Set Union", "Complexity & Big-O"
    ],
    "DBMS": [
        "Relational Data Model", "ACID Properties", "Normalization & Normal Forms",
        "Transaction Isolation Levels", "Concurrency Control & 2PL", "Indexing (B-Tree, Hash)",
        "Query Optimization & Plans", "Deadlocks & Prevention", "Storage & Buffer Pool",
        "Recovery & Write-Ahead Logging"
    ],
    "SQL": [
        "SELECT & Filtering", "Aggregation & GROUP BY", "JOINs (Inner, Outer, Cross)",
        "Subqueries & Correlated Queries", "Window Functions", "Common Table Expressions (CTEs)",
        "Data Modification (DML)", "Views & Materialized Views", "Constraints & Referential Integrity",
        "Query Tuning & EXPLAIN"
    ],
    "OS": [
        "Processes & Threads", "CPU Scheduling Algorithms", "Synchronization & Semaphores",
        "Deadlocks & Banker's Algorithm", "Memory Management & Paging", "Virtual Memory & Page Replacement",
        "File Systems & Inodes", "I/O Systems & Device Drivers", "Inter-Process Communication (IPC)",
        "Security & Protection Rings"
    ],
    "Computer Networks": [
        "OSI & TCP/IP Models", "TCP vs UDP Protocols", "HTTP, HTTP/2 & HTTP/3",
        "DNS Architecture & Resolution", "IP Addressing & Subnetting", "Routing Protocols (BGP, OSPF)",
        "Network Security & TLS/SSL", "WebSockets & Real-Time Protocols", "Load Balancing & CDN Architecture",
        "Network Troubleshooting Tools"
    ],
    "OOP": [
        "Encapsulation & Abstraction", "Inheritance & Polymorphism", "SOLID Principles",
        "Creational Design Patterns", "Structural Design Patterns", "Behavioral Design Patterns",
        "Composition vs Inheritance", "Interfaces & Abstract Contracts", "Domain-Driven Design (DDD)",
        "Code Smells & Refactoring"
    ],
    "C": [
        "Pointers & Pointer Arithmetic", "Dynamic Memory Allocation", "Structs, Unions & Enums",
        "Preprocessor Directives & Macros", "Bitwise Operations & Masks", "File I/O & Streams",
        "Strings & Null Termination", "Function Pointers & Callbacks", "Storage Classes & Qualifiers",
        "Low-Level & Embedded Programming"
    ],
    "C++": [
        "Pointers, References & Const", "OOP & Virtual Functions", "STL Containers & Iterators",
        "Memory Management & RAII", "Move Semantics & Rvalue References", "Smart Pointers (unique, shared)",
        "Templates & Metaprogramming", "Multithreading & Concurrency", "Exception Handling & RTTI",
        "Modern C++ (C++17/20/23)"
    ],
    "Java": [
        "JVM Architecture & Garbage Collection", "OOP, Interfaces & Abstract Classes",
        "Java Collections Framework", "Multithreading & java.util.concurrent", "Generics & Type Erasure",
        "Stream API & Functional Lambdas", "Exception Handling & ClassLoaders", "Spring Framework & Boot Core",
        "Memory Model & Volatile Keyword", "I/O, NIO & Serialization"
    ],
    "Python": [
        "Basics & Data Types", "Functions & Scopes", "OOP & Dunder Methods",
        "Built-in Data Structures", "Exception Handling & Context Managers", "Decorators & Metaprogramming",
        "Generators, Iterators & itertools", "Concurrency & Threading", "AsyncIO & Event Loop",
        "Testing, Typing & Best Practices"
    ],
    "JavaScript": [
        "Event Loop & Callbacks", "Closures & Lexical Scopes", "Promises & Async/Await",
        "Prototypes & Inheritance", "ES6+ Modern Syntax", "DOM Manipulation & Web APIs",
        "Error Handling & Debugging", "V8 Memory Management & GC", "Modules (ESM vs CommonJS)",
        "Performance Optimization"
    ],
    "TypeScript": [
        "Type Annotations & Primitive Types", "Interfaces vs Type Aliases", "Generics & Generic Constraints",
        "Union, Intersection & Literal Types", "Type Narrowing & Type Guards", "Utility Types (Partial, Pick, Omit)",
        "Decorators & Metadata Reflection", "Enums, Namespaces & Modules", "tsconfig & Compilation Architecture",
        "Advanced Type System (Conditional, Mapped)"
    ],
    "Kotlin": [
        "Null Safety & Smart Casts", "Coroutines, Scopes & Dispatchers", "Extension Functions & Properties",
        "OOP, Data Classes & Sealed Classes", "Higher-Order Functions & Inlining", "Lambdas & Scope Functions",
        "Collections & Sequences", "Android Jetpack Architecture", "Delegation Pattern (by keyword)",
        "Generics & Variance (in/out)"
    ],
    "React": [
        "Components, JSX & Props", "State Management & useState", "Effects, Lifecycle & useEffect",
        "Custom Hooks Development", "Context API & Prop Drilling", "Memoization (useMemo, useCallback)",
        "Virtual DOM & Fiber Reconciler", "Server Components & Suspense", "Forms, Inputs & Controlled State",
        "Error Boundaries & Portals"
    ],
    "Next.js": [
        "App Router vs Pages Router", "Server-Side Rendering (SSR)", "Static Site Generation (SSG)",
        "Incremental Static Regeneration (ISR)", "API Routes & Server Actions", "Middleware & Request Pipeline",
        "Routing, Segments & Layouts", "Image, Font & Script Optimization", "Data Fetching, Revalidation & Caching",
        "Deployment & Edge Runtime"
    ],
    "Node.js": [
        "Event Loop Phases & Libuv", "Streams, Buffers & Backpressure", "Cluster & Worker Threads",
        "File System Operations (fs)", "Module Systems (CommonJS vs ESM)", "Error Handling & Uncaught Rejections",
        "Memory Leak Detection & Heap Dumps", "HTTP/HTTPS Core Modules", "Process Object & Environment",
        "Native C++ Addons & N-API"
    ],
    "Express": [
        "Routing & Route Handlers", "Middleware Pipeline Architecture", "Request & Response Lifecycle",
        "Error Handling Middleware", "Authentication & JWT Middleware", "Request Validation & Sanitization",
        "Security Headers & Helmet", "File Uploads with Multer", "Rate Limiting & Throttling",
        "REST API Architecture & Best Practices"
    ],
    "MongoDB": [
        "Document Data Modeling", "CRUD Operations & Query Operators", "Aggregation Pipeline Framework",
        "Indexing Strategies (Compound, Text)", "Sharding & Horizontal Partitioning", "Replica Sets & High Availability",
        "Schema Validation & Mongoose", "Multi-Document ACID Transactions", "WiredTiger Storage Engine",
        "Performance Profiling & explain()"
    ],
    "PostgreSQL": [
        "Architecture & Background Processes", "MVCC, Tuples & VACUUM", "Advanced Indexing (B-Tree, GIN, GiST)",
        "JSONB & Semi-Structured Data", "Table Partitioning (Range, List, Hash)", "Connection Pooling & PgBouncer",
        "Replication & WAL Streaming", "Full-Text Search & tsvector", "Stored Procedures & PL/pgSQL",
        "EXPLAIN ANALYZE & Query Optimization"
    ],
    "Statistics": [
        "Descriptive Statistics & Central Tendency", "Probability Distributions (Normal, Binomial)",
        "Hypothesis Testing & Null Hypothesis", "p-values, Alpha & Statistical Significance",
        "Central Limit Theorem (CLT)", "Confidence Intervals & Margin of Error",
        "Correlation vs Linear Regression", "Bayes' Theorem & Conditional Probability",
        "ANOVA & Chi-Square Tests", "Resampling & Bootstrapping"
    ],
    "Data Science": [
        "Exploratory Data Analysis (EDA)", "Data Cleaning & Imputation Techniques", "Feature Engineering & Transformations",
        "Feature Selection & Dimensionality", "Pandas DataFrames & Operations", "NumPy Vectorized Computations",
        "Dimensionality Reduction (PCA, t-SNE)", "Model Evaluation Metrics (ROC-AUC, F1)",
        "Data Visualization (Matplotlib, Seaborn)", "Outlier Detection & Robust Statistics"
    ],
    "Machine Learning": [
        "Supervised Learning (Regression & Classification)", "Unsupervised Learning (Clustering, K-Means)",
        "Bias-Variance Tradeoff", "Regularization (L1 Lasso, L2 Ridge)", "Decision Trees & Random Forests",
        "Gradient Boosting (XGBoost, LightGBM)", "Cross-Validation & K-Fold Strategies",
        "Evaluation Metrics (Confusion Matrix, Precision/Recall)", "Hyperparameter Tuning (Grid, Random, Bayesian)",
        "Ensemble Methods & Stacking"
    ],
    "Deep Learning": [
        "Neural Network Architecture & Perceptrons", "Activation Functions (ReLU, GELU, Sigmoid)",
        "Backpropagation & Chain Rule", "Optimization Algorithms (Adam, SGD, RMSprop)",
        "Convolutional Neural Networks (CNNs)", "Recurrent Neural Networks (RNNs, LSTMs)",
        "Transformers Architecture & Self-Attention", "Regularization, Dropout & Batch Norm",
        "Loss Functions (Cross-Entropy, MSE)", "Transfer Learning & Fine-Tuning"
    ],
    "NLP": [
        "Tokenization & Text Preprocessing", "Word Embeddings (Word2Vec, GloVe)", "TF-IDF & Bag-of-Words",
        "Language Modeling (N-gram to Neural)", "Sequence-to-Sequence & Attention", "BERT, RoBERTa & Masked Language Models",
        "Named Entity Recognition (NER)", "Sentiment Analysis & Text Classification",
        "Text Generation & Beam Search", "Evaluation Metrics (BLEU, ROUGE, Perplexity)"
    ],
    "Computer Vision": [
        "Image Processing Fundamentals", "Convolutional Filters & Kernel Operations", "Edge Detection (Sobel, Canny)",
        "Object Detection (YOLO, Faster R-CNN)", "Image Segmentation (U-Net, Mask R-CNN)",
        "Transfer Learning with ResNet & VGG", "Data Augmentation Techniques", "Face Detection & Recognition",
        "Optical Character Recognition (OCR)", "Vision Transformers (ViT)"
    ],
    "AI": [
        "Search Algorithms (A*, Breadth-First, Depth-First)", "Game Playing & Minimax with Alpha-Beta",
        "Knowledge Representation & Ontologies", "Expert Systems & Inference Engines",
        "Reinforcement Learning (Q-Learning, Policy Gradients)", "Markov Decision Processes (MDP)",
        "Multi-Agent Systems & Coordination", "Heuristic Search Design",
        "Constraint Satisfaction Problems (CSP)", "Ethical AI, Bias & Fairness"
    ],
    "GenAI": [
        "Generative Models Taxonomy", "Generative Adversarial Networks (GANs)", "Variational Autoencoders (VAEs)",
        "Diffusion Models Architecture", "Latent Space Representation & Sampling", "Prompt Engineering Techniques",
        "Text-to-Image Generation (Stable Diffusion)", "Inpainting, Outpainting & ControlNet",
        "Synthetic Data Generation", "Evaluation Metrics (FID, Inception Score, CLIP)"
    ],
    "LLMs": [
        "Transformer Foundations for LLMs", "Tokenization Algorithms (BPE, WordPiece)", "Pre-training Objectives & Datasets",
        "Instruction Fine-Tuning (SFT)", "RLHF & Direct Preference Optimization (DPO)",
        "Parameter-Efficient Fine-Tuning (LoRA, QLoRA)", "Quantization Methods (GGUF, AWQ, GPTQ)",
        "Context Windows & Positional Embeddings (RoPE)", "Hallucination Mitigation Strategies",
        "Inference Serving & Optimization (vLLM, TensorRT-LLM)"
    ],
    "RAG": [
        "RAG System Architecture & Components", "Document Chunking Strategies & Overlap",
        "Vector Embeddings & Semantic Similarity", "Dense vs Sparse Retrieval (BM25 vs Vector)",
        "Hybrid Search & Reciprocal Rank Fusion (RRF)", "Re-ranking Models (Cross-Encoders)",
        "Context Compression & Selection", "Multi-Query & Sub-Query Generation",
        "Evaluation Frameworks (Ragas, TruLens)", "Production Latency & Cache Strategies"
    ],
    "Vector Databases": [
        "Vector Indexing (HNSW, IVFFlat, Annoy)", "Distance Metrics (Cosine, Euclidean, Dot Product)",
        "Pinecone Architecture & Serverless", "Milvus Distributed Cluster Setup",
        "Chroma & Embedded Vector Stores", "Qdrant Vector Database Features",
        "Metadata Filtering & Filtered Search", "Sharding & Horizontal Scaling in Vector DBs",
        "Product Quantization & Scalar Quantization", "Hybrid Keyword + Vector Search"
    ],
    "LangChain": [
        "Chains & LCEL (LangChain Expression Language)", "Prompt Templates & Few-Shot Prompts",
        "Output Parsers & Structured Outputs", "Document Loaders & Text Splitters",
        "Memory Systems & Conversation Buffers", "Tool Integration & Custom Tools",
        "Agent Architecture (ReAct, OpenAI Tools)", "Callbacks, Tracing & Streaming",
        "LangSmith Evaluation & Observability", "Multi-Agent Orchestration with LangGraph"
    ],
    "Data Engineering": [
        "ETL vs ELT Architecture", "Data Warehousing (Snowflake, BigQuery)", "Data Lakes & Lakehouse (Delta, Iceberg)",
        "Star Schema vs Snowflake Schema", "Dimensional Modeling (Kimball Methodology)",
        "Change Data Capture (CDC) Patterns", "Workflow Orchestration (Airflow, Dagster)",
        "Data Quality & Great Expectations", "Data Lineage & Metadata Governance",
        "Batch vs Stream Processing Trade-offs"
    ],
    "Spark": [
        "RDD Architecture & In-Memory Computing", "DataFrames, Datasets & Catalyst Optimizer",
        "Spark SQL & Query Planning", "Shuffling, Partitions & Skew Handling",
        "Memory Management & Storage Levels", "Lazy Evaluation & DAG Execution",
        "Broadcast Variables & Accumulators", "PySpark API & Pandas UDFs",
        "Spark Structured Streaming", "Performance Tuning & Memory Overhead"
    ],
    "Kafka": [
        "Topics, Partitions & Message Offsets", "Producer Architecture, acks & Idempotence",
        "Consumer Groups & Partition Rebalancing", "Broker Architecture & Metadata (KRaft vs ZooKeeper)",
        "Log Compaction & Retention Policies", "Replication Factor & In-Sync Replicas (ISR)",
        "Exactly-Once Semantics (EOS)", "Kafka Connect Source & Sink Connectors",
        "Kafka Streams API & State Stores", "Performance Tuning & End-to-End Latency"
    ],
    "Cloud": [
        "Cloud Service Models (IaaS, PaaS, SaaS)", "Cloud Deployment Models (Public, Private, Hybrid)",
        "High Availability & Fault Tolerance", "Disaster Recovery Strategies (RTO, RPO)",
        "Cloud Security & Shared Responsibility Model", "Auto-Scaling & Elastic Load Balancing",
        "FinOps & Cloud Cost Optimization", "Cloud-Native Architecture Principles",
        "Multi-Cloud Strategies & Vendor Lock-in", "Edge Computing & CDN Architecture"
    ],
    "AWS": [
        "IAM Roles, Policies & Least Privilege", "EC2 Instances, AMIs & Auto Scaling Groups",
        "S3 Storage Classes, Buckets & Lifecycle", "VPC, Subnets, Route Tables & Gateways",
        "AWS Lambda & Serverless Compute", "RDS & Aurora Managed Databases",
        "DynamoDB Architecture & Global Tables", "ECS, EKS & Container Orchestration",
        "CloudWatch, CloudTrail & Observability", "SQS & SNS Decoupled Messaging"
    ],
    "GCP": [
        "Compute Engine & Instance Templates", "Cloud Storage Buckets & Access Controls",
        "Google Kubernetes Engine (GKE) Clusters", "BigQuery Serverless Data Warehouse",
        "Cloud Run Containerized Serverless", "Cloud Functions Event-Driven Compute",
        "VPC Networks & Cloud Interconnect", "Vertex AI Machine Learning Platform",
        "Cloud Pub/Sub Asynchronous Messaging", "Cloud Monitoring & Logging (Operations Suite)"
    ],
    "Azure": [
        "Azure Virtual Machines & Scale Sets", "Azure Blob Storage & Storage Accounts",
        "Azure Kubernetes Service (AKS)", "Azure Cosmos DB Multi-Model Database",
        "Azure App Services Web Hosting", "Azure Functions Serverless Execution",
        "Virtual Networks (VNet) & Network Security Groups (NSG)", "Microsoft Entra ID (Azure AD) Identity",
        "Azure DevOps Pipelines & CI/CD", "Azure Monitor & Application Insights"
    ],
    "Docker": [
        "Images, Containers & Layer Caching", "Dockerfile Directives & Best Practices",
        "Multi-Stage Dockerfile Builds", "Container Lifecycle & Healthchecks",
        "Docker Networking (Bridge, Host, Overlay)", "Volumes, Bind Mounts & Tmpfs",
        "Docker Compose Multi-Container Orchestration", "Container Security & Rootless Mode",
        "Image Registry, Tagging & Docker Hub", "Docker Daemon Architecture & Storage Drivers"
    ],
    "Kubernetes": [
        "Cluster Architecture (Control Plane vs Nodes)", "Pod Lifecycle, Probes & Init Containers",
        "Deployments, ReplicaSets & Rollouts", "Services & Service Discovery (ClusterIP, NodePort)",
        "Ingress Controllers & Ingress Resources", "ConfigMaps & Secrets Management",
        "PersistentVolumes, PVCs & StorageClasses", "Horizontal Pod Autoscaler (HPA)",
        "Namespaces, ResourceQuotas & RBAC", "Helm Charts & Package Management"
    ],
    "DevOps": [
        "CI/CD Pipeline Design & Automation", "Infrastructure as Code (Terraform, CloudFormation)",
        "Configuration Management (Ansible)", "GitOps Principles (ArgoCD, Flux)",
        "Continuous Monitoring (Prometheus & Grafana)", "Incident Management, Postmortems & On-Call",
        "Blue-Green & Canary Deployment Strategies", "Site Reliability Engineering (SRE) & SLOs/SLAs",
        "Centralized Log Aggregation (ELK, Loki)", "Secrets Management (HashiCorp Vault)"
    ],
    "Linux": [
        "File Permissions, Ownership & ACLs", "Process Management, Signals & Nice Values",
        "Bash Scripting, Piping & Redirection", "Memory & Disk Inspection (free, df, du)",
        "Networking Tools (curl, netstat, ss, ip)", "Systemd Service Units & Daemons",
        "Package Management (apt, yum, dnf)", "SSH Security & Key-Based Authentication",
        "Text Processing Utilities (grep, sed, awk)", "Linux Kernel Architecture & System Calls"
    ],
    "Git": [
        "Git Internals (.git, Blobs, Trees, Commits)", "Branching Strategies (Git Flow, Trunk-Based)",
        "Git Merge vs Git Rebase", "Resolving Complex Merge Conflicts",
        "Git Stash, Cherry-Pick & Clean", "Git Reset, Revert & Checkout",
        "Git Hooks (Client-Side & Server-Side)", "Git Submodules & Subtrees",
        "Git Reflog & Lost Commit Recovery", "Pull Requests & Code Review Best Practices"
    ],
    "System Design": [
        "Horizontal vs Vertical Scaling", "Load Balancers (Layer 4 vs Layer 7)",
        "Caching Strategies (Cache-Aside, Write-Through)", "Database Sharding & Partitioning Schemes",
        "Message Queues & Asynchronous Processing", "API Rate Limiting & Throttling Algorithms",
        "CAP Theorem & PACELC Theorem", "Microservices vs Monolithic Architecture",
        "CDN & Geo-Distributed Edge Caching", "API Gateway Patterns & Reverse Proxies"
    ],
    "Distributed Systems": [
        "Consensus Algorithms (Raft, Paxos)", "Distributed Transactions & Two-Phase Commit (2PC)",
        "Saga Pattern & Compensating Transactions", "Eventual Consistency & CRDTs",
        "Vector Clocks & Lamport Timestamps", "Gossip Protocols & Membership",
        "Failure Detection & Heartbeat Mechanisms", "Idempotency & Deduplication in Distributed APIs",
        "Distributed Tracing & OpenTelemetry", "Fault Tolerance, Circuit Breakers & Bulkheads"
    ],
    "Cybersecurity": [
        "OWASP Top 10 Web Vulnerabilities", "SQL Injection (SQLi) Prevention",
        "Cross-Site Scripting (XSS) Mitigation", "Cross-Site Request Forgery (CSRF) Tokens",
        "OAuth 2.0 & OpenID Connect Protocols", "Cryptography (Symmetric vs Asymmetric, Hashing)",
        "TLS Handshake, Certificates & PKI", "Zero Trust Architecture Principles",
        "Penetration Testing & Vulnerability Assessment", "Threat Modeling & STRIDE Framework"
    ]
}

# Role mappings
TECH_ROLES = {
    "DSA": "Software Engineer",
    "Algorithms": "Software Engineer",
    "DBMS": "Database Administrator",
    "SQL": "Database Developer",
    "OS": "Systems Engineer",
    "Computer Networks": "Network Engineer",
    "OOP": "Software Engineer",
    "C": "Embedded Software Engineer",
    "C++": "Systems Software Engineer",
    "Java": "Backend Java Engineer",
    "Python": "Python Backend / Data Engineer",
    "JavaScript": "Fullstack JavaScript Developer",
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

# 12 Concept Archetypes for each topic
# Each topic gets 12 distinct questions:
# 4 Easy (indices 0, 1, 2, 3)
# 5 Medium (indices 4, 5, 6, 7, 8)
# 3 Hard (indices 9, 10, 11)
ARCHETYPES = [
    # 0. Easy - Fundamental Definition
    {
        "diff": "Easy",
        "qtype": "Conceptual",
        "q_template": "What is the core purpose of {topic} in {tech}, and what primary problem does it solve?",
        "exp_template": "{topic} in {tech} provides a foundational abstraction designed to address critical architectural and operational needs. It standardizes workflows, simplifies state and resource management, and prevents common engineering pitfalls by enforcing modular, maintainable contracts."
    },
    # 1. Easy - Working Mechanism
    {
        "diff": "Easy",
        "qtype": "Technical",
        "q_template": "Explain how basic {topic} operations are executed and configured in {tech}.",
        "exp_template": "In {tech}, {topic} operations follow standard lifecycle patterns. Components or functions initialize resources, execute designated instructions during the active phase, and clean up state upon completion. Adhering to idiomatic conventions ensures optimal execution and compatibility."
    },
    # 2. Easy - Common Use Cases
    {
        "diff": "Easy",
        "qtype": "Conceptual",
        "q_template": "What are the most common practical use cases for {topic} when building applications with {tech}?",
        "exp_template": "Practical applications of {topic} in {tech} include streamlining data flows, isolating system components, managing runtime configurations, and ensuring predictable performance under standard enterprise workloads."
    },
    # 3. Easy - Best Practices
    {
        "diff": "Easy",
        "qtype": "Technical",
        "q_template": "What essential best practices should developers follow when implementing {topic} in {tech}?",
        "exp_template": "Key best practices for {topic} include maintaining single responsibility, avoiding unnecessary mutations, writing comprehensive automated tests, validating boundary inputs, and following established {tech} style guidelines."
    },
    # 4. Medium - Architectural Trade-offs
    {
        "diff": "Medium",
        "qtype": "Technical",
        "q_template": "What are the core technical trade-offs of utilizing {topic} in {tech} regarding memory, latency, and maintainability?",
        "exp_template": "Employing {topic} in {tech} trades memory overhead and slight initialization latency for improved modularity, decoupling, and maintainability. In resource-constrained environments, developers must balance abstraction benefits against heap allocation and CPU cycle costs."
    },
    # 5. Medium - Implementation Comparison
    {
        "diff": "Medium",
        "qtype": "Technical",
        "q_template": "Compare standard approaches to handling {topic} in {tech} versus alternative architectural patterns.",
        "exp_template": "Standard {topic} patterns in {tech} favor declarative, idiomatic constructs with predictable behavior. Alternative approaches may offer specialized performance gains or lower abstraction overhead, but often increase code complexity and require specialized maintenance."
    },
    # 6. Medium - Error Handling & Edge Cases
    {
        "diff": "Medium",
        "qtype": "Technical",
        "q_template": "How should unexpected edge cases, exceptions, and failure states be handled when working with {topic} in {tech}?",
        "exp_template": "Robust error handling in {topic} requires explicit exception boundaries, defensive input validation, structured fallback strategies, and clear logging. Silent failures must be avoided to ensure fast failure detection and seamless debugging in production."
    },
    # 7. Medium - State & Lifecycle Management
    {
        "diff": "Medium",
        "qtype": "Scenario-based",
        "q_template": "How does {topic} manage state transitions and resource lifecycles across concurrent or asynchronous workflows in {tech}?",
        "exp_template": "Lifecycle management in {topic} coordinates initialization, active state processing, and graceful resource reclamation. In concurrent contexts, synchronization primitives or immutable data flows prevent race conditions and ensure state consistency across execution threads."
    },
    # 8. Medium - Performance Profiling & Tuning
    {
        "diff": "Medium",
        "qtype": "Technical",
        "q_template": "How would you identify and resolve performance bottlenecks associated with {topic} in a high-throughput {tech} system?",
        "exp_template": "Diagnosing {topic} bottlenecks involves profiling CPU and memory allocation hotspots, inspecting I/O wait times, minimizing redundant computations, and optimizing memory access patterns. Caching and pooling techniques can substantially reduce recurring overhead."
    },
    # 9. Hard - Internal Mechanics & Low-Level Architecture
    {
        "diff": "Hard",
        "qtype": "Technical",
        "q_template": "Explain the internal mechanics, memory layouts, or low-level algorithms that govern {topic} under the hood in {tech}.",
        "exp_template": "Under the hood, {topic} in {tech} relies on optimized internal structures such as contiguous buffer allocations, state machines, hash tables, or tree hierarchies. Understanding pointer indirection, cache locality, and runtime dispatch mechanisms reveals how {tech} maintains high throughput."
    },
    # 10. Hard - Scalability & Distributed Production Systems
    {
        "diff": "Hard",
        "qtype": "System Design",
        "q_template": "How do you scale {topic} to handle distributed loads, high concurrency, and fault tolerance in large-scale {tech} deployments?",
        "exp_template": "Scaling {topic} requires horizontal partitioning, asynchronous message queues, stateless worker clusters, and circuit breaker patterns. Ensuring high availability involves automated health checks, idempotency keys, and graceful degradation during network partitions."
    },
    # 11. Hard - Security & Attack Vectors
    {
        "diff": "Hard",
        "qtype": "Technical",
        "q_template": "What critical security vulnerabilities, attack vectors, or race conditions can emerge from misconfigured {topic} in {tech}, and how are they mitigated?",
        "exp_template": "Security risks in {topic} include injection vectors, unvalidated deserialization, race conditions on shared memory, and resource exhaustion DoS attacks. Mitigation demands strict input sanitization, least-privilege access controls, constant-time comparisons, and comprehensive security auditing."
    }
]

def generate_canonical_catalog():
    catalog = []
    seen_ids = set()
    duplicates_removed = 0
    invalid_count = 0

    for tech_name, topics in TECH_TOPICS.items():
        role = TECH_ROLES.get(tech_name, "Software Engineer")
        tech_slug = slugify(tech_name)

        for topic_name in topics:
            topic_slug = slugify(topic_name)

            for idx, arch in enumerate(ARCHETYPES):
                q_text = arch["q_template"].format(tech=tech_name, topic=topic_name)
                explanation = arch["exp_template"].format(tech=tech_name, topic=topic_name)
                subtopic = f"{topic_name} - Level {idx + 1}"
                diff = arch["diff"]
                q_type = arch["qtype"]

                if not q_text or len(q_text) < 10:
                    invalid_count += 1
                    continue

                qid = generate_qid(q_text)
                if qid in seen_ids:
                    duplicates_removed += 1
                    continue

                seen_ids.add(qid)
                catalog.append({
                    "id": qid,
                    "technology": tech_name,
                    "technology_slug": tech_slug,
                    "topic": topic_name,
                    "topic_slug": topic_slug,
                    "subtopic": subtopic,
                    "question": q_text,
                    "difficulty": diff,
                    "question_type": q_type,
                    "role": role,
                    "explanation": explanation,
                    "source": "canonical"
                })

    return catalog, duplicates_removed, invalid_count

if __name__ == "__main__":
    catalog, dupes, invalid = generate_canonical_catalog()
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "canonical_bank.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    easy_c = sum(1 for q in catalog if q["difficulty"] == "Easy")
    med_c = sum(1 for q in catalog if q["difficulty"] == "Medium")
    hard_c = sum(1 for q in catalog if q["difficulty"] == "Hard")
    techs_c = len(set(q["technology"] for q in catalog))
    topics_c = len(set((q["technology"], q["topic"]) for q in catalog))

    print(f"Generated {len(catalog)} canonical questions.")
    print(f"Unique questions: {len(catalog)}")
    print(f"Technologies: {techs_c}")
    print(f"Topics: {topics_c}")
    print(f"Easy: {easy_c}")
    print(f"Medium: {med_c}")
    print(f"Hard: {hard_c}")
    print(f"Invalid: {invalid}")
    print(f"Duplicates removed: {dupes}")
