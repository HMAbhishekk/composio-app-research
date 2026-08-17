# Research agent

This is the agent that produced the dataset behind the case study. It researches
one app's public API (auth, self-serve vs gated, API surface, existing MCP,
buildability verdict) using Claude with a live web-search tool, then a second,
separate adversarial agent tries to refute the first agent's claims against
primary sources. See `../README.md` for the full project writeup and the
verification-loop story.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...        # required
export COMPOSIO_API_KEY=comp-...           # optional, adds a Composio toolkit cross-check
```

## Run the research pass

```bash
# smoke test on 3 apps first
python agent.py --ids 1,41,82 --output /tmp/smoke.json

# full 100-app run (takes a while -- each app is a multi-turn agentic search)
python agent.py --output ../data/results_rerun.json --concurrency 4
```

Resumable: if the process dies partway through, just re-run the same command —
it skips ids already present in `--output`.

## Run the verification pass

```bash
# adversarially re-check a random sample of 20 apps from a results file
python verify.py --input ../data/results_pass1.json --sample 20 \
  --output ../verification/pass2_rerun.json

# or check specific apps by id
python verify.py --input ../data/results_pass1.json --ids 1,5,60,77,82,92
```

## Recompute the pattern stats

```bash
python aggregate.py --input ../data/results_final.json --output ../data/pattern_stats.json
```

## Files

| File | What it is |
|---|---|
| `apps.json` | The 100-app research set (copied from `../data/apps.json`) |
| `schema.py` | The structured-output schema every research call is forced into |
| `agent.py` | Pass-1 research agent: web-search + forced structured output per app |
| `verify.py` | Pass-2 adversarial verification agent: tries to refute pass-1 claims |
| `aggregate.py` | Computes the auth/self-serve/MCP/buildability pattern stats |

## Honesty note on reproducibility

Re-running `agent.py` from scratch will **not** produce byte-identical output
to `../data/results_pass1.json` — web content changes over time, and an LLM's
search path isn't deterministic even at temperature 0 with a live web tool.
What *is* reproducible is the **methodology**: same prompt, same forced
schema, same "cite your evidence URL, mark confidence honestly" instruction,
same adversarial verification step. That's the claim this repo makes, and
it's the one that matters for the interview.

The actual dataset used in the deployed case study (`../data/results_final.json`)
was produced by running this exact methodology through parallel subagents in
one research session (documented in `../verification/`), not by executing
`agent.py` end-to-end with a live API key in this repo — see the top-level
README for the full chain of custody.
