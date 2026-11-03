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
        "recommended_configuration",
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

    profiling = context.get(
        "profiling",
        {}
    )

    deterministic_evidence = context.get(
        "deterministic_evidence",
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

        "profiling":
            profiling,

        "deterministic_evidence":
            deterministic_evidence,

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

10. Treat the dedicated benchmark results in the
    performance section as the primary evidence for
    runtime speedup and thread selection.

11. Treat hardware profiling as complementary
    microarchitectural evidence. Profiling may help
    explain IPC, cache, branch, or overhead behavior,
    but it must not replace the dedicated benchmark
    speedup used for the main performance decision.

12. A profiling regression by itself does not require
    rejection when the candidate is correct and the
    dedicated benchmark shows a meaningful speedup.

13. If profiling suggests substantial overhead or poor
    hardware behavior, you may mention it as a reason
    for RETUNE or additional investigation, especially
    when the benchmark speedup is marginal.

14. When discussing hardware profiling, explicitly
    distinguish sequential measurements, OpenMP
    measurements, and comparison/delta measurements.
    Never describe a sequential metric as if it were
    the OpenMP candidate metric.

15. Prefer the profiling comparison fields when
    interpreting whether IPC, cache miss rate, or
    branch miss rate improved or regressed. A positive
    cache-miss-rate or branch-miss-rate change means
    the rate increased; a negative IPC change means
    IPC decreased.

16. Do not claim that profiling shows no overhead when
    the supplied comparison metrics show substantial
    regressions. Report such regressions accurately,
    even if the final decision remains ACCEPT because
    the dedicated benchmark shows useful speedup.

17. The near-tie threshold applies only when comparing
    measured candidate configurations with one another.
    Do not describe an absolute speedup value as being
    within the near-tie threshold.

18. recommended_threads must come from measured
    configurations in the supplied context.

18a. If performance.selection.configuration_dimensions
    contains more than one dimension and a recommended
    configuration exists, return recommended_configuration
    with the exact measured values. For the current
    multidimensional autotuning schema, preserve both
    threads and block_size. Do not invent or combine
    parameter values from different configurations.

18b. recommended_configuration.threads must agree with
    recommended_threads. For a one-dimensional thread-only
    selection, recommended_configuration may be omitted or
    null.

19. If deterministic_evidence is present, treat it as
    the authoritative semantic interpretation of the
    measured data. Do not contradict its derived facts,
    near-tie meaning, or metric assessments.

20. When deterministic_evidence is available, prefer
    citing its derived facts and assessments instead of
    independently reinterpreting raw numeric fields.

21. If raw profiling or performance values appear to
    conflict with deterministic_evidence, follow the
    deterministic evidence and do not invent a new
    interpretation.

22. Distinguish transformation_benefit from
    parallel_benefit. A speedup obtained only with one
    OpenMP thread is not evidence of successful parallel
    scaling.

23. If parallel_status is PARALLEL_SCALING_FAILURE,
    explicitly consider that evidence when deciding
    whether the current parallel strategy should be
    accepted, retuned, modified, or rejected.

24. If profiling is empty or unavailable, do not claim
    that profiling showed good behavior, low overhead,
    or absence of regressions.

25. Keep decision and next_action semantically
    consistent:
    ACCEPT -> PROMOTE_CANDIDATE.
    RETUNE -> RETUNE_CONFIGURATION or
    RUN_MORE_BENCHMARKS.
    MODIFY -> SEND_TO_CODER when the implementation or
    parallel strategy must change.
    REJECT -> REJECT_CANDIDATE.

26. SEND_TO_DEBUGGER is reserved for compilation,
    correctness, or validation failures that require
    repair. Do not send a correct candidate to the
    Debugger merely because its performance is poor.

27. When correctness passes but the current parallel
    strategy fails to scale, distinguish between an
    irrecoverable candidate and a strategy that can be
    modified or retuned. Do not reject a candidate solely
    because its first parallel strategy performs poorly
    when the supplied evidence indicates that the
    strategy should be modified.

22. Keep the reason concise and evidence-based.

23. Return only an object matching the required JSON
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
    context,
    timeout_seconds,
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
            timeout=timeout_seconds,
        ) as response:

            raw_response = (
                response.read()
                .decode(
                    "utf-8"
                )
            )

    except TimeoutError:

        raise RuntimeError(
            "OLLAMA_TIMEOUT: model did not "
            f"finish within {timeout_seconds} seconds."
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

        best_parallel = (
            selection.get(
                "best_parallel"
            )
        )

        if best_parallel:

            measured_threads.add(
                best_parallel.get(
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
    # Complete multidimensional configuration validation.
    # --------------------------------------------------------

    recommended_configuration = (
        decision.get(
            "recommended_configuration"
        )
    )

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

    configuration_dimensions = (
        selection.get(
            "configuration_dimensions",
            [
                "threads",
            ],
        )
    )

    multidimensional = (
        len(
            configuration_dimensions
        )
        > 1
    )

    selection_recommended = (
        selection.get(
            "recommended"
        )
    )

    if (
        multidimensional
        and selection_recommended
        and recommended_configuration
        is None
    ):

        errors.append(
            "multidimensional selection requires "
            "recommended_configuration"
        )

    if (
        recommended_configuration
        is not None
    ):

        configuration_threads = (
            recommended_configuration.get(
                "threads"
            )
        )

        if (
            recommended_threads
            is None
        ):

            errors.append(
                "recommended_configuration requires "
                "recommended_threads"
            )

        elif (
            configuration_threads
            != recommended_threads
        ):

            errors.append(
                "recommended_configuration.threads "
                "must match recommended_threads"
            )

        missing_dimensions = [
            dimension
            for dimension
            in configuration_dimensions
            if dimension
            not in recommended_configuration
        ]

        if missing_dimensions:

            errors.append(
                "recommended_configuration is missing "
                "configuration dimensions: "
                + ", ".join(
                    missing_dimensions
                )
            )

        else:

            measured_configurations = []

            near_tie_candidates = (
                selection.get(
                    "near_tie_candidates",
                    [],
                )
            )

            measured_configurations.extend(
                near_tie_candidates
            )

            for key in [
                "raw_fastest",
                "recommended",
                "best_parallel",
                "best_one_thread",
            ]:

                candidate = (
                    selection.get(
                        key
                    )
                )

                if candidate:

                    measured_configurations.append(
                        candidate
                    )

            measured_tuples = {
                tuple(
                    candidate.get(
                        dimension
                    )
                    for dimension
                    in configuration_dimensions
                )
                for candidate
                in measured_configurations
            }

            requested_tuple = tuple(
                recommended_configuration.get(
                    dimension
                )
                for dimension
                in configuration_dimensions
            )

            if (
                requested_tuple
                not in measured_tuples
            ):

                errors.append(
                    "recommended_configuration was not "
                    "present in measured configurations"
                )

    # --------------------------------------------------------
    # Decision / next_action consistency.
    # --------------------------------------------------------

    decision_name = decision.get(
        "decision"
    )

    next_action = decision.get(
        "next_action"
    )

    allowed_actions_by_decision = {
        "ACCEPT": {
            "PROMOTE_CANDIDATE",
        },

        "RETUNE": {
            "RETUNE_CONFIGURATION",
            "RUN_MORE_BENCHMARKS",
        },

        "MODIFY": {
            "SEND_TO_CODER",
            "SEND_TO_DEBUGGER",
        },

        "REJECT": {
            "REJECT_CANDIDATE",
        },
    }

    valid_actions = (
        allowed_actions_by_decision.get(
            decision_name,
            set(),
        )
    )

    if (
        valid_actions
        and next_action not in valid_actions
    ):

        errors.append(
            f"{decision_name} cannot use "
            f"{next_action}"
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
        "TCC2 COORDINATOR AGENT v0.2"
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
        ),
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help=(
            "Maximum Ollama execution time "
            "in seconds."
        ),
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
                context,
                args.timeout,
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
