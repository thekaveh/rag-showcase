# 2.4 Running Graph Approaches Locally

The vector approaches (`vanilla-rag`, `hybrid-rag`, `contextual-rag` and their
flavors) run cleanly on any Atlas-supported source. The **graph approaches**
(`graph-rag`, `lazy-graph-rag`, `agentic-rag`) additionally depend on LightRAG's
knowledge-graph **extraction**, which is the heaviest local step and carries a few
host-specific footguns. This page is the runbook for a clean local graph run.

First, confirm the graph is actually built — `make eval-check` reports the LightRAG
knowledge-graph population, not just service health:

```bash
make eval-check
# ...
#   [live  ] ✓ lightrag  healthy; graph: 40 processed / 0 failed / 0 in-flight doc(s)
```

An empty graph while the manifest declares graph aliases is a hard failure (the
false-green this check exists to catch). `0 processed` or `N failed` means
extraction did not complete — work through the sections below.

## Known blocker: extract runaway (upstream)

LightRAG entity extraction runs native to Ollama with no output cap, so a chunk
that trips the extract model into non-terminating generation blocks the drain until
a coarse 1800s worker timeout fires, and enough of them stall the whole ingest.
Symptoms in `docker logs <project>-lightrag`:

```text
extract LLM func: Worker execution timeout after 1800s
Failed to extract document N/40
```

This is an upstream Atlas defect —
[thekaveh/atlas#796](https://github.com/thekaveh/atlas/issues/796) — and there is no
reliable consumer-side fix until it lands (a per-call `num_predict` cap / enforced
timeout). Until then, watch `eval-check`'s graph counts rather than assuming a green
service means a populated graph.

## Host Ollama: version parity

A skew between the Ollama **CLI** and the running **server** (for example, the
desktop app auto-updates while a Homebrew CLI stays behind) can wedge a run. Check
it directly:

```bash
ollama --version
# ollama version is 0.32.1
# Warning: client version is 0.21.0   <- skew
```

`make eval-check` surfaces this as an advisory. To fix, update the CLI to match the
server and restart the Ollama app so both agree.

## Host Ollama: keep models resident during ingest

A graph ingest churns three host models — `mistral-small3.2:24b` (extract),
`nomic-embed-text` (embed), and `qwen3.6:latest` (keyword). Under Ollama defaults
the large models can evict each other between calls (`ollama ps` shows
`Stopping...`), thrashing the run. Pin them **for the duration of a run**, then
revert:

```bash
launchctl setenv OLLAMA_KEEP_ALIVE -1
launchctl setenv OLLAMA_MAX_LOADED_MODELS 4
# quit and reopen the Ollama app so the running server picks up the change
```

Revert once the run is done:

```bash
launchctl unsetenv OLLAMA_KEEP_ALIVE
launchctl unsetenv OLLAMA_MAX_LOADED_MODELS
# quit and reopen the Ollama app
ollama stop mistral-small3.2:24b qwen3.6:latest nomic-embed-text
```

`OLLAMA_KEEP_ALIVE=-1` keeps every loaded model resident **forever** — roughly
66 GB for these three, visible as two large `llama-server` processes in Activity
Monitor. That is the setting working as intended, not a leak; revert it when you are
done so idle models unload normally. See
[thekaveh/atlas#798](https://github.com/thekaveh/atlas/issues/798) for the upstream
request to size `keep_alive` automatically for host-Ollama ingest.

## After a run: restore the infra pin

Starting the stack can check the vendored `infra/` submodule out to a newer Atlas
commit and stage that drift in your working tree — so a later `git commit -am` would
silently bump the pin. Restore it after any run:

```bash
git restore --staged infra
git -C infra checkout "$(git ls-tree HEAD infra | awk '{print $3}')"
git status   # clean, infra back at the pinned SHA
```

This is tracked upstream as
[thekaveh/atlas#797](https://github.com/thekaveh/atlas/issues/797); the consumer-side
guard is [rag-showcase#96](https://github.com/thekaveh/rag-showcase/issues/96).

## See also

- [Quick Start](quickstart.md) — the one-command bring-up.
- [Hardware Sizing](../hardware.md) — minimum and recommended local profiles.
