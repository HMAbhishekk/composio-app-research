#!/usr/bin/env python3
"""
agent.py -- the research agent for the AI Product Ops take-home.

What it does
------------
For each app in apps.json, spins up a Claude agent with a native web-search
tool. The agent searches the app's real developer docs, reads them, and then
calls a forced structured-output tool (`record_app_research`, defined in
schema.py) to report:

  - one_liner, auth_methods, self_serve status + evidence
  - api_surface, existing_mcp (+ detail)
  - buildability_verdict, blocker
  - evidence_url, confidence, notes

Optionally cross-checks each app against Composio's own toolkit catalog
(if COMPOSIO_API_KEY is set) as an extra ground-truth signal -- if Composio
already ships a toolkit for the app, that's strong evidence the app is
buildable today, and we surface Composio's own auth-scheme metadata
alongside the agent's independent findings.

This is the same methodology used to produce data/results_pass1.json in this
repo -- that dataset was produced by running this exact prompt/schema
through parallel research agents. Re-running this script from scratch will
not reproduce byte-identical results (web content changes, and LLM search
paths vary run to run), but it will reproduce the same *kind* of findings,
which is the honest, load-bearing claim: reproducible methodology, not
reproducible bytes.

Usage
-----
    export ANTHROPIC_API_KEY=sk-ant-...
    # optional, adds a Composio ground-truth cross-check:
    export COMPOSIO_API_KEY=comp-...

    python agent.py                          # research all 100 apps
    python agent.py --limit 10                # just the first 10 (smoke test)
    python agent.py --ids 1,5,41,60            # specific apps by id
    python agent.py --concurrency 5            # parallel workers (default 4)
    python agent.py --output ../data/results_rerun.json

Resume support: the script skips any id already present in --output, so a
killed/interrupted run can just be re-invoked to pick up where it left off.
"""
import argparse
import concurrent.futures
import json
import os
import sys
import threading
import time
from pathlib import Path

from schema import APP_RESULT_SCHEMA

try:
    import anthropic
except ImportError:
    print("Missing dependency: pip install -r requirements.txt", file=sys.stderr)
    raise

MODEL = "claude-sonnet-4-5-20250929"
MAX_SEARCH_TURNS = 6  # safety cap on agentic back-and-forth per app

SYSTEM_PROMPT = """You are a research agent building an "agent-toolkit buildability" \
dataset, as part of a larger project figuring out which SaaS apps could \
become AI-agent-callable tool integrations (Composio-style research).

For the app you're given, use your web_search tool to find and read the \
app's REAL developer/API documentation -- do not answer from memory alone. \
Verify auth method, self-serve vs gated access, API surface, and whether an \
MCP server (official or community) exists, against the actual current docs. \
If you cannot confirm something after a genuine search attempt, report it \
honestly with low confidence rather than inventing an answer -- accuracy is \
the top priority of this project, and an honest "couldn't verify" beats a \
confident guess.

Once you've done enough research to answer confidently (or you've \
genuinely exhausted reasonable search attempts), call the \
`record_app_research` tool with your structured findings. Do not call it \
before you've actually searched."""


def build_user_prompt(app: dict) -> str:
    return (
        f"App: {app['app']}\n"
        f"Category: {app['category']}\n"
        f"Website / hint: {app['hint']}\n\n"
        "Research this app's public API: auth method(s), whether a developer "
        "can self-serve credentials or whether it's gated (paid plan / admin "
        "approval / contact-sales), the API surface (REST/GraphQL, how "
        "broad), whether an MCP server already exists for it, and an overall "
        "buildability verdict for turning it into an agent toolkit today. "
        "Cite the actual URL you used as evidence."
    )


def research_one_app(client: anthropic.Anthropic, app: dict, composio_index: dict | None) -> dict:
    """Run the agentic search-then-record loop for a single app."""
    messages = [{"role": "user", "content": build_user_prompt(app)}]
    tools = [
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 8},
        {
            "name": APP_RESULT_SCHEMA["name"],
            "description": APP_RESULT_SCHEMA["description"],
            "input_schema": APP_RESULT_SCHEMA["input_schema"],
        },
    ]

    result = None
    for turn in range(MAX_SEARCH_TURNS):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        record_call = next(
            (b for b in resp.content if getattr(b, "type", None) == "tool_use"
             and b.name == "record_app_research"),
            None,
        )
        if record_call is not None:
            result = dict(record_call.input)
            break

        if resp.stop_reason == "end_turn":
            # Model stopped without calling our tool -- nudge it once.
            messages.append({
                "role": "user",
                "content": (
                    "Please call record_app_research now with your findings "
                    "so far (mark confidence low for anything unverified)."
                ),
            })
            continue

        # stop_reason == "tool_use" but only server-side web_search tools were
        # used (already resolved by the API) -- nothing for us to do except
        # let the loop continue so the model can keep searching or answer.

    if result is None:
        result = {
            "one_liner": "(agent failed to converge on a structured answer)",
            "auth_methods": ["Other"],
            "self_serve": "gated",
            "self_serve_evidence": "",
            "api_surface": "",
            "existing_mcp": "no",
            "existing_mcp_detail": "",
            "buildability_verdict": "blocked",
            "blocker": f"Agent did not produce a result within {MAX_SEARCH_TURNS} turns.",
            "evidence_url": "",
            "confidence": "low",
            "notes": "AUTOMATION FAILURE -- needs a human researcher to redo this one by hand.",
        }

    result["id"] = app["id"]
    result["app"] = app["app"]
    result["category"] = app["category"]

    # Optional Composio ground-truth cross-check.
    if composio_index is not None:
        hit = composio_index.get(app["app"].lower())
        result["composio_toolkit_exists"] = hit is not None
        if hit:
            result["composio_auth_scheme"] = hit.get("auth_scheme")
            result["notes"] += (
                f" [Composio cross-check] A Composio toolkit already exists "
                f"for this app (auth scheme per Composio: "
                f"{hit.get('auth_scheme', 'unknown')}) -- strong independent "
                f"confirmation this app is buildable today."
            )

    return result


def load_composio_index() -> dict | None:
    """Best-effort: list Composio's own toolkit catalog as a ground-truth
    signal. Returns {app_name_lowercase: {...}} or None if no API key / the
    composio package isn't installed / the call fails -- this is a bonus
    signal, not a hard dependency."""
    api_key = os.environ.get("COMPOSIO_API_KEY")
    if not api_key:
        return None
    try:
        from composio import Composio
    except ImportError:
        print("COMPOSIO_API_KEY set but `composio` package not installed "
              "(pip install composio), skipping Composio cross-check.",
              file=sys.stderr)
        return None
    try:
        client = Composio(api_key=api_key)
        toolkits = client.toolkits.list()  # SDK surface as of composio>=0.7
        index = {}
        for tk in getattr(toolkits, "items", toolkits):
            name = getattr(tk, "name", None) or getattr(tk, "slug", None)
            if not name:
                continue
            index[name.lower()] = {
                "auth_scheme": getattr(tk, "auth_schemes", None) or getattr(tk, "auth_scheme", None),
            }
        return index
    except Exception as exc:  # noqa: BLE001 -- this is a best-effort bonus signal
        print(f"Composio cross-check unavailable ({exc}); continuing without it.",
              file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apps-file", default="apps.json")
    parser.add_argument("--output", default="../data/results_rerun.json")
    parser.add_argument("--limit", type=int, default=None, help="only research the first N apps")
    parser.add_argument("--ids", default=None, help="comma-separated app ids to research, e.g. 1,5,41")
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY first. See README.md.", file=sys.stderr)
        sys.exit(1)

    apps = json.loads(Path(args.apps_file).read_text())
    if args.ids:
        wanted = {int(x) for x in args.ids.split(",")}
        apps = [a for a in apps if a["id"] in wanted]
    elif args.limit:
        apps = apps[: args.limit]

    out_path = Path(args.output)
    existing = {}
    if out_path.exists():
        existing = {d["id"]: d for d in json.loads(out_path.read_text())}
        apps = [a for a in apps if a["id"] not in existing]
        if apps:
            print(f"Resuming: {len(existing)} already done, {len(apps)} remaining.")
        else:
            print(f"Nothing to do -- all {len(existing)} requested apps already in {out_path}.")
            return

    composio_index = load_composio_index()
    if composio_index is not None:
        print(f"Composio cross-check enabled ({len(composio_index)} toolkits indexed).")

    client = anthropic.Anthropic()
    lock = threading.Lock()
    results = list(existing.values())

    def worker(app):
        try:
            r = research_one_app(client, app, composio_index)
        except Exception as exc:  # noqa: BLE001
            r = {
                "id": app["id"], "app": app["app"], "category": app["category"],
                "one_liner": "", "auth_methods": ["Other"], "self_serve": "gated",
                "self_serve_evidence": "", "api_surface": "", "existing_mcp": "no",
                "existing_mcp_detail": "", "buildability_verdict": "blocked",
                "blocker": f"Exception during research: {exc}",
                "evidence_url": "", "confidence": "low",
                "notes": "AUTOMATION FAILURE -- needs a human researcher.",
            }
        with lock:
            results.append(r)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(sorted(results, key=lambda d: d["id"]), indent=2))
            print(f"[{len(results)}] {app['app']} -> {r.get('buildability_verdict', '?')} "
                  f"({r.get('confidence', '?')} confidence)")

    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(worker, apps))

    print(f"Done in {time.time() - start:.0f}s. Wrote {len(results)} results to {out_path}")


if __name__ == "__main__":
    main()
