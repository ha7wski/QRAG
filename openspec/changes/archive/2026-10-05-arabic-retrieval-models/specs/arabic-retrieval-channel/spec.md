## ADDED Requirements

### Requirement: The dense channel is off by default
`SEARCH_DENSE_AR_ENABLED` SHALL default to `0`. With it off, `GET /search` SHALL return exactly
the results it returned before this change and SHALL load no model it did not load before.

#### Scenario: Flag off
- **WHEN** the backend runs without `SEARCH_DENSE_AR_ENABLED`
- **THEN** `GET /search` returns, for every gold query, the same ranked verse ids as before the change

#### Scenario: Rollback
- **WHEN** the flag is removed from `.env` and the backend restarted
- **THEN** the previous behaviour is restored with no code change

### Requirement: One encoder instance in the process
The dense channel SHALL use the chat path's embedder instance and Qdrant client; it SHALL NOT
construct a second encoder or a second Qdrant client.

#### Scenario: Shared instance
- **WHEN** the channel embeds a query
- **THEN** it uses the object returned by `HybridSearch.embedder` of the chat engine's retriever

#### Scenario: Model mismatch
- **WHEN** the shared embedder's model differs from the model recorded in the collection's points
- **THEN** the channel returns no ids, logs the mismatch once, and `/search` builds its pool as before

### Requirement: The Arabic collection is separate and reusable by the chat
Arabic verse vectors SHALL be stored in the collection named by `QDRANT_COLLECTION_AR`, with the
same point ids, payload fields and payload indexes as the existing collection, plus `emb_model`
and `emb_format`. The build SHALL refuse a name equal to `QDRANT_COLLECTION`, and SHALL never
recreate, write or delete the existing collection.

#### Scenario: Name collision
- **WHEN** `build_index_ar.py` runs with `QDRANT_COLLECTION_AR` equal to `QDRANT_COLLECTION`
- **THEN** it exits with an error before touching the store

#### Scenario: Chat-compatible payload
- **WHEN** a point of the Arabic collection is read
- **THEN** it carries every field `qdrant_store._payload` writes, and filtering by `surah_number`, `period` or `juz` works as on the existing collection

### Requirement: Dense candidates enter the pool by reciprocal rank fusion
When the channel returns ids, `/search` SHALL order the union of the root, BM25 and dense
candidate lists by `Σ 1/(60 + rank)`, cap it at `SEARCH_RERANK_POOL_MAX`, honour the route's
filters, and leave reranking, coverage blending, the AND policy and the threshold unchanged.

#### Scenario: Filter respected
- **WHEN** `/search?q=…&surah=2` runs with the channel on
- **THEN** every dense candidate in the pool belongs to surah 2

#### Scenario: Matches the benchmark
- **WHEN** the gold queries run through `/search` with the channel on
- **THEN** the ranked ids match the benchmark's C-rrf run
