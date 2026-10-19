# ADR 0003: Unified Relational and Vector Storage via PostgreSQL 16 with pgvector

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Data & Security Team (Stream A, C, E)

---

## Context and Problem Statement
The AI Assistant and RAG capabilities require storing and retrieving embeddings of approved documentation, model cards, and generated reports alongside traditional relational entities (plans, assets, audit trails, and user roles).
Should a standalone vector database (e.g., Pinecone, Qdrant, Chroma, Milvus) be deployed, or should PostgreSQL handle both relational data and vector embeddings?

## Considered Options
1. **Standalone Vector Database** (Qdrant / Milvus / Chroma) + PostgreSQL.
2. **PostgreSQL 16 + `pgvector` Extension** for hybrid relational, full-text (`tsvector`), and vector retrieval.

## Decision Outcome
Chosen option: **PostgreSQL 16 + `pgvector`** (Option 2).

### Rationale
- **Unified Transactional Boundary:** Document chunks, metadata, and embeddings can be queried in join operations with user role permissions and document versions.
- **Role-Scoped Security:** pgvector queries naturally integrate with SQL row-level security and `WHERE role IN (...)` filters, preventing cross-tenant or unauthorized knowledge leakage.
- **Single Datastore Operability:** Eliminates the need to maintain, back up, and synchronize consistency between a separate vector database and the primary PostgreSQL database.
- **Hybrid Retrieval:** PostgreSQL supports combining vector cosine similarity with full-text search (`ts_rank`) for balanced precision and keyword fidelity.
