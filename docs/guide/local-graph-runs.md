# 2.4 Running Graph Approaches Locally

The vector approaches (`vanilla-rag`, `hybrid-rag`, `contextual-rag` and their
flavors) run cleanly on any Atlas-supported source. The LightRAG-backed
`graph-rag` path and the graph tool available to `agentic-rag` depend on LightRAG's
knowledge-graph **extraction**, which is the heaviest local step and carries a few
host-specific footguns. Experimental `lazy-graph-rag` is independent of LightRAG
extraction: it reads the profile's Weaviate chunks and persists its deterministic
concept graph in a dedicated JSON cache volume. This page is the runbook for a clean
local graph run.

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

## 1. Known blocker: extract runaway (upstream)

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

## 2. Host Ollama: version parity

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

## 3. Host Ollama: keep models resident during ingest

A graph ingest alternates between two host models — `qwen3.8:latest` (extract and
keyword) and `nomic-embed-text` (embed). Under Ollama defaults, concurrent work
can still trigger model churn (`ollama ps` shows
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
ollama stop qwen3.8:latest nomic-embed-text
```

`OLLAMA_KEEP_ALIVE=-1` keeps every loaded model resident **forever** — roughly
the resident footprint reported by `ollama ps`. That is the setting working as
intended, not a leak; revert it when you are
done so idle models unload normally. See
[thekaveh/atlas#798](https://github.com/thekaveh/atlas/issues/798) for the upstream
request to size `keep_alive` automatically for host-Ollama ingest.

## 4. After a run: the infra pin

Starting the stack can check the vendored `infra/` submodule out to a newer Atlas
commit and stage that drift in your working tree — so a later `git commit -am`
could silently bump the pin. `scripts/start-all.sh` restores the pinned SHA
automatically on every exit (success or failure) via an EXIT trap
([rag-showcase#96](https://github.com/thekaveh/rag-showcase/issues/96)), so a
wrapper-driven run leaves the repo clean with no manual step. The commands below
are only needed if you launched Atlas directly (`infra/start.sh …`, bypassing the
wrapper) or want to verify the tree is clean:

```bash
git restore --staged infra
git -C infra checkout "$(git ls-tree HEAD infra | awk '{print $3}')"
git status   # clean, infra back at the pinned SHA
```

The underlying launcher behavior is tracked upstream as
[thekaveh/atlas#797](https://github.com/thekaveh/atlas/issues/797).

## 5. See also

- [Quick Start](quickstart.md) — the one-command bring-up.
- [Hardware Sizing](../hardware.md) — minimum and recommended local profiles.
