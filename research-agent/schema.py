"""
Shared JSON schema for one researched app entry.

This is the exact structure both the live agent (agent.py) and the
verification pass (verify.py) are instructed to fill in. Keeping it in one
place means the prompt, the parser, and the case-study renderer never drift
out of sync with each other.
"""

APP_RESULT_SCHEMA = {
    "name": "record_app_research",
    "description": "Record structured research findings for one app's agent-toolkit buildability.",
    "input_schema": {
        "type": "object",
        "properties": {
            "one_liner": {
                "type": "string",
                "description": "What the app does, one sentence.",
            },
            "auth_methods": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "OAuth2", "API Key", "Basic Auth", "Bearer Token",
                        "JWT", "Other", "N/A - local CLI tool",
                    ],
                },
                "description": "All auth types the public API supports.",
            },
            "self_serve": {
                "type": "string",
                "enum": ["self-serve", "gated", "mixed"],
                "description": (
                    "self-serve: a developer can get working credentials "
                    "themselves, free or on trial, no sales call. "
                    "gated: needs a paid plan tier, admin/partner approval, "
                    "or contact-sales. mixed: some access self-serve, "
                    "deeper access gated."
                ),
            },
            "self_serve_evidence": {
                "type": "string",
                "description": "One sentence explaining the self_serve verdict.",
            },
            "api_surface": {
                "type": "string",
                "description": "REST/GraphQL/etc, and roughly how broad.",
            },
            "existing_mcp": {
                "type": "string",
                "enum": ["yes-official", "yes-community", "no"],
            },
            "existing_mcp_detail": {
                "type": "string",
                "description": "Name of MCP repo/package found, or why none exists.",
            },
            "buildability_verdict": {
                "type": "string",
                "enum": ["ready-now", "ready-with-friction", "blocked"],
            },
            "blocker": {
                "type": "string",
                "description": "Main blocker if not ready-now, else 'none'.",
            },
            "evidence_url": {
                "type": "string",
                "description": "The actual docs/article URL used as primary evidence.",
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": (
                    "high = fetched and read current docs; medium = search "
                    "snippets + partial doc read; low = could not verify well "
                    "-- use this honestly rather than guessing."
                ),
            },
            "notes": {
                "type": "string",
                "description": "Anything else notable (rate limits, sandboxes, deprecations).",
            },
        },
        "required": [
            "one_liner", "auth_methods", "self_serve", "self_serve_evidence",
            "api_surface", "existing_mcp", "existing_mcp_detail",
            "buildability_verdict", "blocker", "evidence_url",
            "confidence", "notes",
        ],
    },
}
