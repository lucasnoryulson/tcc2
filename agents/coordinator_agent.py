import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = (
    "http://localhost:11434/api/chat"
)

DEFAULT_MODEL = "qwen2.5:3b"


# ============================================================
# DECISION SCHEMA
# ============================================================

DECISION_SCHEMA = {
    "type": "object",

    "properties": {

        "decision": {
            "type": "string",
            "enum": [
                "ACCEPT",
                "RETUNE",
                "MODIFY",
                "REJECT",
            ],
        },

        "recommended_threads": {
            "type": [
                "integer",
                "null",
            ],
        },

        "reason": {
            "type": "string",
        },

        "next_action": {
            "type": "string",
            "enum": [
                "PROMOTE_CANDIDATE",
                "RUN_MORE_BENCHMARKS",
                "RETUNE_CONFIGURATION",
                "SEND_TO_CODER",
                "SEND_TO_DEBUGGER",
                "REJECT_CANDIDATE",
            ],
        },

        "risk": {
            "type": "string",
            "enum": [
                "LOW",
                "MEDIUM",
                "HIGH",
            ],
        },

        "evidence_used": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },

    "required": [
        "decision",
        "recommended_threads",
        "reason",
        "next_action",
        "risk",
        "evidence_used",
    ],

    "additionalProperties": False,
}


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(path):
    return json.loads(
        path.read_text()
    )


# ============================================================
# CONTEXT COMPACTION
# ============================================================

def compact_context(context):
    """
    Keep the evidence useful for coordinator decisions
    while avoiding unnecessary prompt size.
    """

    source = context.get(
        "source",
        {}
    )

    pattern = context.get(
        "pattern",
        {}
    )

    strategy = context.get(
        "strategy",
        {}
    )

    validation = context.get(
        "validation",
        {}
    )

    performance = context.get(
        "performance",
        {}
    )

    dependence = context.get(
        "dependence_analysis",
        {}
    )

    return {
        "task":
            context.get(
                "task"
            ),

        "sequential_code":
            source.get(
                "sequential_code"
            ),

        "candidate_code":
            source.get(
                "candidate_code"
            ),

        "pattern":
            pattern,

        "strategy":
            strategy,

        "dependence_analysis":
            dependence,

        "validation":
            validation,

        "performance":
            performance,

        "agent_constraints":
            context.get(
                "agent_constraints",
                []
            ),
    }


# ============================================================
# PROMPT
# ============================================================

def build_system_prompt():
    return """
You are the Coordinator Agent in a research system for
automatic OpenMP parallelization.

You do NOT generate code in this step.

Your responsibility is to decide what should happen to
the current generated parallel candidate using only the
evidence supplied to you.

You must obey these rules:

1. Correctness is mandatory.
   If correctness validation did not PASS, never ACCEPT.

2. Measured evidence is more important than speculation.

3. Never contradict dependency constraints reported by
   the deterministic analysis.

4. If a candidate is correct and provides a meaningful
   measured speedup, ACCEPT is allowed.

5. When several thread configurations have practically
   equivalent performance, prefer the deterministic
   resource-aware recommendation unless there is strong
   evidence against it.

6. RETUNE means:
   the transformation itself appears valid, but further
   performance configuration should be explored.

7. MODIFY means:
   the code transformation should be changed by the
   Coder Agent.

8. REJECT means:
   the candidate is unsafe, incorrect, or provides no
   useful path forward.

9. Do not invent benchmark results.

10. recommended_threads must come from measured
    configurations in the supplied context.

11. Keep the reason concise and evidence-based.

12. Return only an object matching the required JSON
    schema.
""".strip()


def build_user_prompt(context):

    compact = compact_context(
        context
    )

    return (
        "Evaluate the following automatic OpenMP "
        "parallelization candidate.\n\n"
        "RESEARCH CONTEXT:\n"
        + json.dumps(
            compact,
            indent=2
        )
        + "\n\n"
        "Choose exactly one decision:\n"
        "ACCEPT, RETUNE, MODIFY, or REJECT.\n\n"
        "If the candidate is accepted, use "
        "PROMOTE_CANDIDATE as next_action.\n"
        "If more performance configurations should be "
        "tested, use RETUNE_CONFIGURATION or "
        "RUN_MORE_BENCHMARKS.\n"
        "If code must change, use SEND_TO_CODER.\n"
        "If a correctness/compilation problem requires "
        "repair, use SEND_TO_DEBUGGER.\n"
    )


# ============================================================
# OLLAMA
# ============================================================

def call_ollama(
    model,
    context
):

    payload = {
        "model":
            model,

        "messages": [
            {
                "role":
                    "system",

                "content":
                    build_system_prompt(),
            },
            {
                "role":
                    "user",

                "content":
                    build_user_prompt(
                        context
                    ),
            },
        ],

        "stream":
            False,

        "format":
            DECISION_SCHEMA,

        "options": {
            "temperature":
                0,
        },
    }

    body = json.dumps(
        payload
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={
            "Content-Type":
                "application/json",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=600,
        ) as response:

            raw_response = (
                response.read()
                .decode(
                    "utf-8"
                )
            )

    except urllib.error.URLError as error:

        raise RuntimeError(
            "Could not connect to Ollama at "
            f"{OLLAMA_URL}: {error}"
        )

    response_data = json.loads(
        raw_response
    )

    message = response_data.get(
        "message",
        {}
    )

    content = message.get(
        "content"
    )

    if not content:

        raise RuntimeError(
            "Ollama returned an empty response."
        )

    try:

        decision = json.loads(
            content
        )

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "Model response was not valid JSON: "
            f"{error}\n\n"
            f"Raw content:\n{content}"
        )

    metadata = {
        "model":
            response_data.get(
                "model"
            ),

        "total_duration":
            response_data.get(
                "total_duration"
            ),

        "load_duration":
            response_data.get(
                "load_duration"
            ),

        "prompt_eval_count":
            response_data.get(
                "prompt_eval_count"
            ),

        "eval_count":
            response_data.get(
                "eval_count"
            ),

        "done_reason":
            response_data.get(
                "done_reason"
            ),
    }

    return decision, metadata


# ============================================================
# RESPONSE VALIDATION
# ============================================================

def validate_decision(
    decision,
    context
):

    errors = []

    allowed_decisions = {
        "ACCEPT",
        "RETUNE",
        "MODIFY",
        "REJECT",
    }

    allowed_actions = {
        "PROMOTE_CANDIDATE",
        "RUN_MORE_BENCHMARKS",
        "RETUNE_CONFIGURATION",
        "SEND_TO_CODER",
        "SEND_TO_DEBUGGER",
        "REJECT_CANDIDATE",
    }

    allowed_risks = {
        "LOW",
        "MEDIUM",
        "HIGH",
    }

    if (
        decision.get(
            "decision"
        )
        not in allowed_decisions
    ):

        errors.append(
            "invalid decision"
        )

    if (
        decision.get(
            "next_action"
        )
        not in allowed_actions
    ):

        errors.append(
            "invalid next_action"
        )

    if (
        decision.get(
            "risk"
        )
        not in allowed_risks
    ):

        errors.append(
            "invalid risk"
        )

    # --------------------------------------------------------
    # Safety check:
    # ACCEPT requires correctness PASS.
    # --------------------------------------------------------

    correctness = (
        context.get(
            "validation",
            {}
        )
        .get(
            "correctness_gate"
        )
    )

    if (
        decision.get(
            "decision"
        )
        == "ACCEPT"
        and correctness != "PASS"
    ):

        errors.append(
            "ACCEPT forbidden because "
            "correctness did not PASS"
        )

    # --------------------------------------------------------
    # Thread recommendation must correspond to one
    # measured OpenMP configuration.
    # --------------------------------------------------------

    recommended_threads = (
        decision.get(
            "recommended_threads"
        )
    )

    if recommended_threads is not None:

        selection = (
            context.get(
                "performance",
                {}
            )
            .get(
                "selection",
                {}
            )
        )

        candidates = (
            selection.get(
                "near_tie_candidates",
                []
            )
        )

        measured_threads = {
            candidate.get(
                "threads"
            )
            for candidate
            in candidates
        }

        raw_fastest = (
            selection.get(
                "raw_fastest"
            )
        )

        if raw_fastest:

            measured_threads.add(
                raw_fastest.get(
                    "threads"
                )
            )

        recommended = (
            selection.get(
                "recommended"
            )
        )

        if recommended:

            measured_threads.add(
                recommended.get(
                    "threads"
                )
            )

        if (
            recommended_threads
            not in measured_threads
        ):

            errors.append(
                "recommended_threads was not "
                "present in measured configurations"
            )

    # --------------------------------------------------------
    # ACCEPT should promote.
    # --------------------------------------------------------

    if (
        decision.get(
            "decision"
        ) == "ACCEPT"
        and decision.get(
            "next_action"
        )
        != "PROMOTE_CANDIDATE"
    ):

        errors.append(
            "ACCEPT must use "
            "PROMOTE_CANDIDATE"
        )

    return errors


# ============================================================
# PRINTING
# ============================================================

def print_decision(
    decision,
    metadata
):

    print(
        "================================="
    )

    print(
        "TCC2 COORDINATOR AGENT v0.1"
    )

    print(
        "================================="
    )

    print(
        f"Model: "
        f"{metadata.get('model')}"
    )

    print()

    print(
        f"Decision: "
        f"{decision.get('decision')}"
    )

    print(
        f"Recommended threads: "
        f"{decision.get('recommended_threads')}"
    )

    print(
        f"Risk: "
        f"{decision.get('risk')}"
    )

    print(
        f"Next action: "
        f"{decision.get('next_action')}"
    )

    print()

    print(
        "Reason:"
    )

    print(
        f"  {decision.get('reason')}"
    )

    print()

    print(
        "Evidence used:"
    )

    for evidence in decision.get(
        "evidence_used",
        []
    ):

        print(
            f"  - {evidence}"
        )

    print()

    print(
        "LLM metadata:"
    )

    print(
        f"  Prompt tokens: "
        f"{metadata.get('prompt_eval_count')}"
    )

    print(
        f"  Output tokens: "
        f"{metadata.get('eval_count')}"
    )

    print(
        f"  Done reason: "
        f"{metadata.get('done_reason')}"
    )

    print(
        "================================="
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "context",
        type=Path,
        help=(
            "JSON produzido pelo "
            "Agent Context Builder."
        )
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    context_file = (
        args.context.resolve()
    )

    if not context_file.exists():

        print(
            f"Arquivo não encontrado: "
            f"{context_file}"
        )

        sys.exit(1)

    context = load_json(
        context_file
    )

    print(
        "Calling Coordinator Agent..."
    )

    print(
        f"Model: {args.model}"
    )

    try:

        decision, metadata = (
            call_ollama(
                args.model,
                context
            )
        )

    except RuntimeError as error:

        print(
            f"AGENT_ERROR: {error}"
        )

        sys.exit(1)

    errors = validate_decision(
        decision,
        context
    )

    if errors:

        print(
            "AGENT_RESPONSE_REJECTED"
        )

        for error in errors:

            print(
                f"  - {error}"
            )

        print()

        print(
            "Raw decision:"
        )

        print(
            json.dumps(
                decision,
                indent=2
            )
        )

        sys.exit(1)

    if args.output:

        output_file = (
            args.output.resolve()
        )

    else:

        output_file = (
            context_file.parent
            / "dot_coordinator_decision.json"
        )

    final_output = {
        "schema":
            "tcc2-coordinator-decision",

        "version":
            "0.1",

        "model":
            args.model,

        "decision":
            decision,

        "llm_metadata":
            metadata,
    }

    output_file.write_text(
        json.dumps(
            final_output,
            indent=2
        )
    )

    print_decision(
        decision,
        metadata
    )

    print()

    print(
        f"Decision salva em: "
        f"{output_file}"
    )


if __name__ == "__main__":
    main()
