## ADDED Requirements

### Requirement: The adoption rule is frozen before the first measurement
The benchmark SHALL compute its verdicts with the rule recorded in this change's design (D4:
reference, primary set and metric, paired bootstrap with 10 000 resamples and seed 0, guard
tolerances). The rule, the candidate list and the query instruction SHALL NOT be changed after
any benchmark number has been produced; a change to any of them SHALL be a new, separately
recorded run.

#### Scenario: Verdict computed, not chosen
- **WHEN** the benchmark finishes
- **THEN** each decision (D-enc, D-chan, D-rr) is reported as `win` / `no win` with the bootstrap interval and every guard value that produced it

#### Scenario: No winner
- **WHEN** no candidate's interval lower bound exceeds 0 for a decision
- **THEN** the report states "keep the current model" for that decision and no candidate is promoted

### Requirement: Only verified, openly licensed weights are benchmarked
Every candidate model SHALL be public and ungated on the Hugging Face Hub, ship safetensors
weights and declare a licence. Each candidate SHALL be loaded and prompted exactly as its model
card specifies (query and passage prefixes, instructions, padding side, scoring head).

#### Scenario: Unpublished model
- **WHEN** a requested model has no public weights (Swan-Large)
- **THEN** it is listed as excluded with the reason, and the benchmark runs without it

#### Scenario: Baseline measured as documented and as deployed
- **WHEN** the baseline encoder is benchmarked
- **THEN** it appears twice — with today's `query: `/`passage: ` text, and with its card's instruct format — and the encoder decision's reference is the card's format

### Requirement: The benchmark never touches production state
The benchmark SHALL NOT open, create or modify any Qdrant collection, SHALL NOT write under
`data/`, and SHALL NOT run while the backend or a loaded Ollama model is resident. Dense
retrieval SHALL be brute-force cosine over in-memory vectors.

#### Scenario: Backend running
- **WHEN** the benchmark starts while the backend port answers
- **THEN** it exits with an error naming the process to stop, before loading any model

### Requirement: `/search` is measured through its own code
Configuration B SHALL call the production `api.routers.search.search` function, with only the
reranker swapped. Configuration C SHALL first prove that, with zero dense candidates, it
returns B's ranked ids for every gold query.

#### Scenario: Parity broken
- **WHEN** configuration C with `N_DENSE = 0` differs from B on any gold query
- **THEN** the benchmark aborts before printing any configuration C number

### Requirement: Reproducible outputs
The benchmark SHALL write a Markdown comparison table and a raw JSON file holding, per model,
variant and configuration, every per-query ranked list and metric, the model revision hashes,
latency (median, p95) and peak memory.

#### Scenario: Re-run
- **WHEN** the benchmark is run twice on the same revisions
- **THEN** the metric values and verdicts are identical
