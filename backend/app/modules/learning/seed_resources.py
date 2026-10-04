import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.learning.model import LearningResource

logger = logging.getLogger(__name__)

CURATED_LEARNING_RESOURCES = [
    # Python
    {
        "title": "Official Python Tutorial & Language Reference",
        "description": "Comprehensive official Python documentation covering data structures, object-oriented programming, standard libraries, and concurrency.",
        "topic": "Python",
        "canonical_skill": "Python",
        "difficulty": "Beginner",
        "resource_type": "Documentation",
        "url": "https://docs.python.org/3/tutorial/",
        "estimated_duration_mins": 60,
        "source": "Python Software Foundation",
        "quality_rating": 4.9,
    },
    {
        "title": "Python Concurrency, Asyncio & Memory Internals",
        "description": "Deep dive into Python GIL, memory management, generator coroutines, and event loop architecture with asyncio.",
        "topic": "Python",
        "canonical_skill": "Python",
        "difficulty": "Advanced",
        "resource_type": "Article",
        "url": "https://realpython.com/async-io-python/",
        "estimated_duration_mins": 45,
        "source": "Real Python",
        "quality_rating": 4.8,
    },
    # FastAPI
    {
        "title": "FastAPI Official Tutorial - User Guide",
        "description": "Step-by-step official guide to modern async Python APIs, dependency injection, Pydantic schemas, and security.",
        "topic": "FastAPI",
        "canonical_skill": "FastAPI",
        "difficulty": "Beginner",
        "resource_type": "Documentation",
        "url": "https://fastapi.tiangolo.com/tutorial/",
        "estimated_duration_mins": 50,
        "source": "FastAPI Documentation",
        "quality_rating": 5.0,
    },
    {
        "title": "Mastering FastAPI Dependency Injection & Middleware",
        "description": "Advanced architectural patterns in FastAPI: sub-dependencies, DB connection pooling, rate limiting, and CORS.",
        "topic": "FastAPI",
        "canonical_skill": "FastAPI",
        "difficulty": "Advanced",
        "resource_type": "Tutorial",
        "url": "https://fastapi.tiangolo.com/tutorial/dependencies/",
        "estimated_duration_mins": 40,
        "source": "FastAPI Documentation",
        "quality_rating": 4.9,
    },
    # JavaScript / TypeScript
    {
        "title": "MDN Web Docs - Modern JavaScript Guide",
        "description": "Definitive reference for closures, prototypes, event loops, promises, async/await, and ES6+ syntax.",
        "topic": "JavaScript",
        "canonical_skill": "JavaScript",
        "difficulty": "Intermediate",
        "resource_type": "Documentation",
        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
        "estimated_duration_mins": 50,
        "source": "Mozilla Developer Network",
        "quality_rating": 4.9,
    },
    {
        "title": "TypeScript Handbook & Type System Mastery",
        "description": "Comprehensive guide to generics, utility types, discriminated unions, mapped types, and strict mode.",
        "topic": "TypeScript",
        "canonical_skill": "TypeScript",
        "difficulty": "Intermediate",
        "resource_type": "Documentation",
        "url": "https://www.typescriptlang.org/docs/handbook/intro.html",
        "estimated_duration_mins": 45,
        "source": "Microsoft TypeScript Docs",
        "quality_rating": 4.8,
    },
    # React
    {
        "title": "Official React Documentation - Thinking in React",
        "description": "Master component lifecycles, hooks (useState, useEffect, useMemo, useCallback), state synchronization, and component hierarchy.",
        "topic": "React",
        "canonical_skill": "React",
        "difficulty": "Beginner",
        "resource_type": "Documentation",
        "url": "https://react.dev/learn",
        "estimated_duration_mins": 60,
        "source": "React Dev",
        "quality_rating": 4.9,
    },
    # SQL / PostgreSQL
    {
        "title": "PostgreSQL Performance Optimization & Indexing",
        "description": "Query plan analysis (EXPLAIN ANALYZE), B-Tree, GIN, and GiST indexes, partitioning, and transactional isolation levels.",
        "topic": "PostgreSQL",
        "canonical_skill": "PostgreSQL",
        "difficulty": "Advanced",
        "resource_type": "Documentation",
        "url": "https://www.postgresql.org/docs/current/performance-tips.html",
        "estimated_duration_mins": 60,
        "source": "PostgreSQL Global Development Group",
        "quality_rating": 4.9,
    },
    {
        "title": "SQL Query Mastery & Relational Schema Design",
        "description": "Advanced joins, window functions (ROW_NUMBER, RANK, DENSE_RANK), aggregations, CTEs, and schema normalization.",
        "topic": "SQL",
        "canonical_skill": "SQL",
        "difficulty": "Intermediate",
        "resource_type": "Tutorial",
        "url": "https://mode.com/sql-tutorial/",
        "estimated_duration_mins": 45,
        "source": "Mode Analytics",
        "quality_rating": 4.7,
    },
    # Data Structures & Algorithms
    {
        "title": "Dynamic Programming: 1D to 2D Memoization Patterns",
        "description": "Foundational guide to recognizing optimal substructure, overlapping subproblems, state transitions, and tabulation.",
        "topic": "Dynamic Programming",
        "canonical_skill": "Dynamic Programming",
        "difficulty": "Advanced",
        "resource_type": "Tutorial",
        "url": "https://leetcode.com/explore/learn/card/dynamic-programming/",
        "estimated_duration_mins": 60,
        "source": "LeetCode Learning",
        "quality_rating": 4.8,
    },
    {
        "title": "Graph Algorithms: BFS, DFS, Dijkstra & Topological Sort",
        "description": "In-depth visual guide to graph representations (adjacency list vs matrix), cycle detection, shortest paths, and bipartite checks.",
        "topic": "Graphs",
        "canonical_skill": "Graphs",
        "difficulty": "Intermediate",
        "resource_type": "Practice Set",
        "url": "https://leetcode.com/explore/learn/card/graph/",
        "estimated_duration_mins": 60,
        "source": "LeetCode Learning",
        "quality_rating": 4.8,
    },
    {
        "title": "Binary Trees, BSTs & Lowest Common Ancestor Patterns",
        "description": "Master tree recursions, preorder/inorder/postorder traversals, height-balanced validation, and BST operations.",
        "topic": "Trees",
        "canonical_skill": "Trees & Binary Search Trees",
        "difficulty": "Intermediate",
        "resource_type": "Tutorial",
        "url": "https://leetcode.com/explore/learn/card/data-structures-and-algorithms/",
        "estimated_duration_mins": 50,
        "source": "LeetCode Learning",
        "quality_rating": 4.7,
    },
    # System Design & Architecture
    {
        "title": "System Design Primer - Scalability & Distributed Systems",
        "description": "Learn how to design systems at scale: load balancers, caching, CDN, message queues (Kafka/RabbitMQ), CAP theorem, and database sharding.",
        "topic": "System Design",
        "canonical_skill": "System Design",
        "difficulty": "Advanced",
        "resource_type": "Article",
        "url": "https://github.com/donnemartin/system-design-primer",
        "estimated_duration_mins": 90,
        "source": "System Design Primer",
        "quality_rating": 5.0,
    },
    {
        "title": "REST API Architecture Best Practices",
        "description": "Idempotency, HTTP status codes, pagination, rate limiting headers, error schemas, and OpenAPI specification.",
        "topic": "REST APIs",
        "canonical_skill": "REST APIs",
        "difficulty": "Intermediate",
        "resource_type": "Article",
        "url": "https://restfulapi.net/",
        "estimated_duration_mins": 30,
        "source": "RESTful API Guidelines",
        "quality_rating": 4.8,
    },
    # Docker & DevOps
    {
        "title": "Docker Containerization Fundamentals & Multi-Stage Builds",
        "description": "Learn Dockerfile best practices, container lifecycle, layer caching, volume mounting, and docker compose orchestration.",
        "topic": "Docker",
        "canonical_skill": "Docker",
        "difficulty": "Intermediate",
        "resource_type": "Documentation",
        "url": "https://docs.docker.com/get-started/",
        "estimated_duration_mins": 45,
        "source": "Docker Documentation",
        "quality_rating": 4.8,
    },
]


async def seed_learning_resources_if_needed(db: AsyncSession) -> int:
    """Seeds the learning_resources table if empty."""
    res = await db.execute(select(LearningResource).limit(1))
    if res.scalar_one_or_none() is not None:
        return 0

    inserted = 0
    for item in CURATED_LEARNING_RESOURCES:
        resource = LearningResource(**item)
        db.add(resource)
        inserted += 1

    await db.commit()
    logger.info(f"Seeded {inserted} curated learning resources.")
    return inserted
