#!/usr/bin/env python3
"""
aggregate.py -- compute the pattern-analysis stats the case study is built
from (auth-method distribution, self-serve vs gated by category, MCP
coverage by category, buildability verdicts, etc).

    python aggregate.py --input ../data/results_final.json --output ../data/pattern_stats.json
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def compute(data: list[dict]) -> dict:
    n = len(data)
    auth = Counter()
    for d in data:
        for a in d.get("auth_methods", []):
            auth[a] += 1

    self_serve = Counter(d["self_serve"] for d in data)
    buildability = Counter(d["buildability_verdict"] for d in data)
    mcp = Counter(d["existing_mcp"] for d in data)
    confidence = Counter(d["confidence"] for d in data)

    by_cat_ss = defaultdict(Counter)
    by_cat_bv = defaultdict(Counter)
    by_cat_mcp = defaultdict(Counter)
    for d in data:
        by_cat_ss[d["category"]][d["self_serve"]] += 1
        by_cat_bv[d["category"]][d["buildability_verdict"]] += 1
        by_cat_mcp[d["category"]][d["existing_mcp"]] += 1

    return {
        "total_apps": n,
        "auth_methods": dict(auth),
        "self_serve": dict(self_serve),
        "buildability": dict(buildability),
        "existing_mcp": dict(mcp),
        "confidence": dict(confidence),
        "self_serve_by_category": {k: dict(v) for k, v in by_cat_ss.items()},
        "buildability_by_category": {k: dict(v) for k, v in by_cat_bv.items()},
        "mcp_by_category": {k: dict(v) for k, v in by_cat_mcp.items()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="../data/results_final.json")
    ap.add_argument("--output", default="../data/pattern_stats.json")
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text())
    stats = compute(data)
    Path(args.output).write_text(json.dumps(stats, indent=2))
    print(f"Wrote {args.output}: {stats['total_apps']} apps analyzed.")


if __name__ == "__main__":
    main()
