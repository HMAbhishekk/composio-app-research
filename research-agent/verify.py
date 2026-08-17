#!/usr/bin/env python3
"""
verify.py -- the independent verification pass.

Takes a results file produced by agent.py (or the shipped
data/results_pass1.json), samples N apps, and spins up a SEPARATE agent per
sampled app whose only job is to try to REFUTE the original claim against
primary sources -- not to reproduce the research, but to adversarially check
it. This mirrors exactly how data/results_final.json was produced from
data/results_pass1.json in this repo (see verification/pass2_verification.json
for that actual run's output).

Why adversarial, not just "redo the research": asking a fresh agent to
"research this app" tends to reproduce the same search paths and the same
mistakes. Asking it to specifically hunt for reasons the ORIGINAL claim is
wrong is a different task, and catches different errors (stale MCP-existence
claims in particular, since new MCP servers ship weekly and neither pass has
a reliable way to know its own knowledge is stale without being told to look
for it).

Usage
-----
    export ANTHROPIC_API_KEY=sk-ant-...
    python verify.py --input ../data/results_pass1.json --sample 20 --output ../verification/pass2_rerun.json
    python verify.py --input ../data/results_pass1.json --ids 1,5,60,77,82,92
"""
import argparse
import json
import os
import random
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Missing dependency: pip install -r requirements.txt", file=sys.stderr)
    raise

MODEL = "claude-sonnet-4-5-20250929"

VERIFY_SCHEMA = {
    "name": "record_verification",
    "description": "Record the outcome of adversarially checking a research claim.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["confirmed", "partially_correct", "incorrect"],
            },
            "what_was_wrong": {"type": "string", "description": "Empty string if confirmed."},
            "correction": {"type": "string", "description": "Empty string if confirmed."},
            "verification_url": {"type": "string"},
            "my_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": ["verdict", "what_was_wrong", "correction", "verification_url", "my_confidence"],
    },
}

SYSTEM_PROMPT = """You are an independent fact-checker/auditor, not the \
original researcher. You will be shown a claim another agent made about a \
SaaS app's developer API (auth method, self-serve access, MCP existence, \
etc). Your ONLY job is to try to REFUTE it -- search for primary sources \
(official docs, official blog posts, GitHub) using your web_search tool and \
check whether the claim actually holds up right now. Be skeptical, \
especially of specific or impressive claims like "an official MCP server \
exists" -- those are exactly the kind of fact that goes stale fastest. \
Default to "incorrect" or "partially_correct" if you find real evidence \
against the claim; only mark "confirmed" if you positively verified it \
against a live primary source. When you're done, call record_verification."""


def verify_one(client: anthropic.Anthropic, entry: dict) -> dict:
    claim_summary = (
        f"App: {entry['app']} ({entry['category']})\n"
        f"self_serve: {entry['self_serve']} -- {entry.get('self_serve_evidence','')}\n"
        f"auth_methods: {entry.get('auth_methods')}\n"
        f"existing_mcp: {entry['existing_mcp']} -- {entry.get('existing_mcp_detail','')}\n"
        f"buildability_verdict: {entry['buildability_verdict']} -- blocker: {entry.get('blocker','')}\n"
        f"(original evidence URL cited: {entry.get('evidence_url','')})"
    )
    messages = [{"role": "user", "content": f"Verify this claim:\n\n{claim_summary}"}]
    tools = [
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 6},
        {"name": VERIFY_SCHEMA["name"], "description": VERIFY_SCHEMA["description"],
         "input_schema": VERIFY_SCHEMA["input_schema"]},
    ]
    for _ in range(5):
        resp = client.messages.create(model=MODEL, max_tokens=2048, system=SYSTEM_PROMPT,
                                       tools=tools, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        call = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"
                     and b.name == "record_verification"), None)
        if call:
            out = dict(call.input)
            out["app"] = entry["app"]
            out["id"] = entry["id"]
            return out
        if resp.stop_reason == "end_turn":
            messages.append({"role": "user", "content": "Please call record_verification now."})
    return {"app": entry["app"], "id": entry["id"], "verdict": "unverified",
            "what_was_wrong": "", "correction": "", "verification_url": "",
            "my_confidence": "low"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default="../data/results_pass1.json")
    ap.add_argument("--output", default="../verification/pass2_rerun.json")
    ap.add_argument("--sample", type=int, default=20, help="random sample size if --ids not given")
    ap.add_argument("--ids", default=None, help="comma-separated ids to verify instead of random sample")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY first. See README.md.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(Path(args.input).read_text())
    if args.ids:
        wanted = {int(x) for x in args.ids.split(",")}
        sample = [d for d in data if d["id"] in wanted]
    else:
        random.seed(args.seed)
        sample = random.sample(data, min(args.sample, len(data)))

    client = anthropic.Anthropic()
    results = []
    for entry in sample:
        r = verify_one(client, entry)
        results.append(r)
        print(f"{entry['app']}: {r['verdict']}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))

    n = len(results)
    confirmed = sum(1 for r in results if r["verdict"] == "confirmed")
    print(f"\n{confirmed}/{n} fully confirmed ({confirmed/n*100:.0f}%). Wrote {out_path}")


if __name__ == "__main__":
    main()
