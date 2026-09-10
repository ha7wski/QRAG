## ADDED Requirements

### Requirement: The local generation model is named by configuration

The local model backing `LLM_PROVIDER=ollama` SHALL be read from the `OLLAMA_MODEL`
environment variable. The code constant `DEFAULT_OLLAMA_MODEL` and the launcher shell
fallbacks SHALL name the same model as each other, and SHALL apply only when `OLLAMA_MODEL`
is unset. Changing the model in production SHALL require no code edit.

#### Scenario: Environment variable selects the model

- **WHEN** `OLLAMA_MODEL` is set to a model tag present in Ollama
- **THEN** `LLMClient` uses that tag
- **AND** no source file needs modification for the change to take effect

#### Scenario: Defaults agree across code and launchers

- **WHEN** `OLLAMA_MODEL` is unset
- **THEN** `generation/llm_client.py::DEFAULT_OLLAMA_MODEL`, `scripts/run.sh` and
  `local-dev/start.sh` all resolve to the same model tag

#### Scenario: Switching back is one line

- **WHEN** the operator restores the previous value of `OLLAMA_MODEL` and restarts the backend
- **THEN** the previous model serves generation again
- **AND** no other file has to be reverted

### Requirement: The chat template is pinned explicitly

An Ollama model built from a GGUF that carries no embedded chat template SHALL declare a
`TEMPLATE` in its Modelfile. The project SHALL NOT rely on Ollama's template
auto-detection, because a mis-detected template produces degraded output with no error and
no log entry.

#### Scenario: Template is present on the imported model

- **WHEN** `ollama show --modelfile <model>` is run for the local generation model
- **THEN** a non-empty `TEMPLATE` block is printed
- **AND** its generation-role marker matches the model's published `chat_template.jinja`

#### Scenario: Stop tokens accompany the template

- **WHEN** the model is imported
- **THEN** the Modelfile declares the template's turn-terminating tokens as `PARAMETER stop`
- **AND** a generated answer ends at a turn boundary rather than running into the next role header

### Requirement: The model fits the machine's memory budget

The local generation model SHALL be validated to run within available memory before it is
made the default. `num_ctx` SHALL remain at the configured project value and SHALL NOT be
raised to a model's native context length merely because the model supports it.

#### Scenario: Resident cost is measured before the switch

- **WHEN** the candidate model is loaded on the target machine with the rest of the stack running
- **THEN** its resident cost is recorded
- **AND** the switch proceeds only if the model loads without the runtime reporting a
  memory-driven eviction

#### Scenario: A memory failure is treated as a failure

- **WHEN** the inference runtime reports an out-of-memory condition for the GPU backend
- **THEN** the model is NOT considered working
- **AND** the process is restarted before any further measurement is taken, because the
  backend stays in an error state and returns degenerate output for every later request

#### Scenario: Context length stays bounded

- **WHEN** the model declares a native context length larger than the project's `OLLAMA_NUM_CTX`
- **THEN** `OLLAMA_NUM_CTX` is left unchanged
- **AND** the Modelfile's `num_ctx` matches it

### Requirement: Published provenance names the model actually in use

Every generated field the API exposes with an origin tag SHALL report the model that
produced it. The tag SHALL be derived at runtime from the configured provider and model,
never from a literal that can drift.

#### Scenario: Synthesis source follows the configuration

- **WHEN** `OLLAMA_MODEL` names the local model and a synthesis field is generated
- **THEN** `synthesis_source` reports that model tag with the `-local` suffix
- **AND** the value changes automatically when `OLLAMA_MODEL` changes

#### Scenario: Model id is readable without a live backend

- **WHEN** the model id is requested while the Ollama server is unreachable
- **THEN** it is still resolved from the environment
- **AND** it matches the id used as the analysis cache key and the review key

### Requirement: A frozen model recording is bound to its model

A stored recording of model output used as a test fixture SHALL record the model that
produced it, and the replay SHALL assert that recorded model against the currently
configured one. Replaying answers from one model while another serves production SHALL fail
loudly rather than pass silently.

#### Scenario: Replay fails when the model changes

- **WHEN** the configured model differs from `versions.model` in the frozen recording
- **THEN** the replay test fails
- **AND** the failure message names both the recorded model and the configured one

#### Scenario: Re-freezing is deliberate

- **WHEN** the recording is regenerated under a new model
- **THEN** it is produced by an explicit recording command that spends live model calls
- **AND** it is never re-baselined as a side effect of running the test suite

### Requirement: The outgoing model stays available until the new one is validated

The previously configured model SHALL remain installed and selectable until the incoming
model has been measured on the acceptance criteria that motivated the change. Removal of the
outgoing model SHALL be a separate, later step.

#### Scenario: Rollback is possible during validation

- **WHEN** the incoming model is configured but its acceptance measurement has not been recorded
- **THEN** the outgoing model is still installed
- **AND** restoring it requires only a configuration change and a restart

#### Scenario: The register decision is re-measured

- **WHEN** the incoming model is proposed as the new default
- **THEN** the acceptance measurement that the outgoing model failed is repeated against it
- **AND** the recorded verdict names the model it was measured on
