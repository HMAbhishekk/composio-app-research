# 100-App Agent-Toolkit Buildability Study

**Composio — AI Product Ops Intern take-home.**

- **Live page:** _add your GitHub Pages URL here after publishing (see PUBLISH.md)_
- **This repo:** _add your repo URL here after pushing_

One question, 100 apps: for each app, could Composio build an AI-agent-callable
toolkit for it *today*, and if not, exactly what's blocking it? The full writeup —
headline patterns, the 100-app matrix, the agent architecture, and an honest
verification log — is a single self-contained page: **`site/index.html`**.

## What's in this repo

```
data/
  apps.json            the 100-app research set (id, category, app, hint)
  results_pass1.json   raw pass-1 output from the 10 parallel research agents
  results_final.json   pass-1 + every verification-confirmed correction applied
  pattern_stats.json   computed aggregates the case study's charts are built from

research-agent/
  agent.py             the reusable research agent (Claude + web search + forced schema)
  verify.py            the adversarial verification agent
  aggregate.py         recomputes pattern_stats.json from a results file
  schema.py            the shared structured-output contract
  apps.json            copy of data/apps.json for standalone runs
  README.md            how to run agent.py / verify.py yourself

verification/
  pass1_01.json … pass1_10.json    the 10 category batches before merging
  pass2_verification.json          the 20-app adversarial audit trail (what was
                                    checked, the verdict, and every correction)

site/
  index.html            the deliverable — single self-contained HTML case study
  template.html         the same file with data placeholders (for editing)
  apps_data.json        the exact JSON embedded in index.html's table/charts
```

## How this dataset was actually produced (read this — it matters)

Full transparency on chain of custody, since the assignment explicitly asks
for it:

1. **Pass 1 — parallel research.** 10 subagents, one per category (10 apps
   each), each instructed to use live web search and fetch real developer
   docs — not answer from memory — and return a strict 15-field JSON record
   per app (auth methods, self-serve status + evidence, API surface,
   existing-MCP status + detail, buildability verdict + blocker, evidence
   URL, confidence). Merged into `data/results_pass1.json` (100/100 ids,
   zero duplicates, zero gaps — checked programmatically).
2. **Pass 2 — adversarial verification.** A stratified 20-app sample (2 per
   category, biased toward low/medium-confidence and surprising claims) was
   re-checked by *separate* subagents whose only instruction was to try to
   **refute** the pass-1 claim against a live primary source, not reproduce
   the research. Full results in `verification/pass2_verification.json`.
3. **Correction.** Every confirmed error (5 of 20 sampled apps needed a real
   structured-field fix — see the case study's Verification section for the
   full list, including the three MCP-existence claims — ClickUp, Plaid,
   Otter AI — that had simply gone stale between pass 1 and pass 2) was
   patched into `data/results_final.json` with a stated reason. Nothing was
   silently overwritten.
4. **This page** was built from `data/results_final.json` and
   `verification/pass2_verification.json` directly — every number on the
   page traces back to one of those two files.

`research-agent/agent.py` and `research-agent/verify.py` are the **same
methodology, packaged as a standalone, runnable pipeline** — same prompt
structure, same forced schema, same "search real docs, mark confidence
honestly" instruction, same adversarial-refutation verification step. That's
the reproducible claim this repo makes: not byte-identical output on rerun
(web content changes, LLM search paths aren't deterministic), but the same
rigor, runnable by anyone with an `ANTHROPIC_API_KEY`. See
`research-agent/README.md` for exact commands.

## Quick facts (see the live page for the full picture)

- 68/100 apps are `ready-now` — self-serve credentials + documented API,
  buildable today with zero blockers.
- 65/100 are self-serve, 21/100 mixed, 14/100 gated.
- 63/100 already have an official MCP server; another 28 have at least a
  community one.
- Only 5/100 are genuinely blocked, and every one of them is an
  enterprise-sales gate, not a technical one: DealCloud, Gladly, LinkedIn
  Ads, PitchBook, and "Paygent Connect" (which could not even be confirmed
  to exist as a distinct product).
- Pass-1 sample accuracy: 75% (15/20 structured fields fully correct on
  first pass). Post-verification: 100% (20/20) on the corrected dataset —
  see the case study for exactly what was wrong and why.

## Constraints honored

No paid accounts were used for any app. Where an app is gated behind
payment, admin approval, or a sales relationship, that is reported as the
finding itself (with evidence), not treated as a failure to research it. The
few apps that genuinely defeated verification (Paygent Connect, iPayX,
higgsfield) are flagged low-confidence directly on the page rather than
guessed into a false-precision answer.
