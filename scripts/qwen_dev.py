#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import ollama


MODELS = {
    "code": [
        "qwen2.5-coder:14b",
        "qwen2.5-coder:latest",
        "qwen2.5-coder:7b",
        "qwen3:8b",
    ],
    "analysis": [
        "deepseek-r1:14b",
        "qwen3:14b",
        "qwen3:8b",
    ],
    "query": [
        "qwen3:8b",
        "qwen2.5-coder:7b",
        "qwen2.5-coder:latest",
    ],
}


CONTEXT = """
You are a Malt Radar specialist developer.

PROJECT: Malt Radar CLEAN
- Frontend: Flutter/Dart
- Backend: FastAPI + SQLite
- Database: output/import/production.db

CURRENT STATE:
- P42 release candidate commit completed.
- Commit hash: fee57bf.
- P43 legacy data audit completed.
- Legacy data trust: MEDIUM.
- Ollama staging: HOLD.
- Price visibility: OFF in live UI/API.
- Price data must not be used in recommendation, radar, or flavor backfill logic.

CURRENT TASK:
- P44-LEGACY-FLAVOR-BACKFILL

P43 FINDINGS:
- Legacy whiskies: 1,979
- Legacy tasting notes: 496
- Legacy flavor profiles: 894 / 1,979
- Legacy flavor coverage: 45.2%
- Legacy zero-vector profiles: 294
- Legacy page traceability: 0%

TARGET FLAVOR AXES:
- smoky
- peaty
- sherry
- fruity
- sweet
- spicy
- maritime

CONSTRAINTS:
- Start read-only.
- Dry-run first.
- Do not modify production.db without explicit backup/hash/transaction gate.
- Do not overwrite P35/P37 Whisky Advocate flavor profiles.
- Do not use price data.
- Do not include Ollama staging data yet.
- No main branch commits unless explicitly requested.
- Follow AGENTS.md and Malt Radar guardrails.
- Prefer small, traceable, minimum patches.
- Return JSON-serializable results when useful.
"""


def detect_task_type(prompt):
    prompt_lower = prompt.lower()

    code_words = [
        "create",
        "write",
        "generate",
        "implement",
        "add",
        "build",
        "fix",
        "patch",
        "refactor",
    ]

    analysis_words = [
        "review",
        "analyze",
        "analyse",
        "check",
        "assess",
        "evaluate",
        "audit",
        "validate",
        "verify",
    ]

    for word in code_words:
        if word in prompt_lower:
            return "code"

    for word in analysis_words:
        if word in prompt_lower:
            return "analysis"

    return "query"


def get_available_model_names():
    available = ollama.list()

    models = getattr(available, "models", None)

    if models is None and isinstance(available, dict):
        models = available.get("models", [])

    names = []

    for model_obj in models:
        if isinstance(model_obj, dict):
            name = model_obj.get("name") or model_obj.get("model")
        else:
            name = getattr(model_obj, "name", None) or getattr(model_obj, "model", None)

        if name:
            names.append(str(name))

    return names


def get_best_model(task_type, model_override=None):
    if model_override:
        return model_override

    preferences = MODELS.get(task_type, MODELS["query"])

    try:
        available_names = get_available_model_names()
    except Exception as exc:
        print(
            "[ERROR] Ollama model list failed: {}: {}".format(type(exc).__name__, exc),
            file=sys.stderr,
        )
        return "qwen3:8b"

    for wanted in preferences:
        for available in available_names:
            if wanted == available or wanted in available:
                return wanted

    return "qwen3:8b"


def qwen_query(prompt, task_type=None, model=None, temperature=0.3):
    if task_type is None:
        task_type = detect_task_type(prompt)

    selected_model = get_best_model(task_type, model)

    print("")
    print("[{}] Processing {} task...".format(selected_model, task_type), file=sys.stderr)
    print("")

    try:
        response = ollama.generate(
            model=selected_model,
            prompt=CONTEXT + "\n\nTask: " + prompt,
            stream=False,
            options={
                "temperature": temperature,
                "top_p": 0.9,
                "num_predict": 2048,
            },
        )

        if isinstance(response, dict):
            return response.get("response", "")

        return getattr(response, "response", str(response))

    except Exception as exc:
        print(
            "[ERROR] Ollama generate failed: {}: {}".format(type(exc).__name__, exc),
            file=sys.stderr,
        )
        return "Error: {}".format(exc)


def main():
    if len(sys.argv) < 2:
        print("""
Qwen Developer Mode - Malt Radar P44

Usage:
  python scripts/qwen_dev.py "create FastAPI route"
  python scripts/qwen_dev.py "review this function"
  python scripts/qwen_dev.py "what is current P44 target?"
  python scripts/qwen_dev.py -m deepseek-r1:14b "audit this plan"

Requirements:
  1. Ollama running: ollama serve
  2. Models downloaded: ollama list
  3. P44 target: LEGACY-FLAVOR-BACKFILL
  4. Price data must not be used
  5. Ollama staging remains HOLD
""")
        return

    model_override = None

    if "-m" in sys.argv:
        idx = sys.argv.index("-m")

        if idx + 1 >= len(sys.argv):
            print("Error: -m requires a model name")
            return

        model_override = sys.argv[idx + 1]
        prompt = " ".join(sys.argv[idx + 2:])
    else:
        prompt = " ".join(sys.argv[1:])

    if not prompt.strip():
        print("Error: No prompt provided")
        return

    response = qwen_query(prompt, model=model_override)
    print(response)


if __name__ == "__main__":
    main()
