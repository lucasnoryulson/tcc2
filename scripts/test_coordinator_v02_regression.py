import copy
import importlib.util
import json
from pathlib import Path


# ============================================================
# Load Coordinator
# ============================================================

module_path = Path(
    "agents/coordinator_agent.py"
)

spec = importlib.util.spec_from_file_location(
    "coordinator_agent",
    module_path,
)

coordinator = (
    importlib.util.module_from_spec(
        spec
    )
)

spec.loader.exec_module(
    coordinator
)


# ============================================================
# Load multidimensional context
# ============================================================

context_path = Path(
    "results/mac_m5_2026-09-09/"
    "agents/wavefront_tiled_agent_context.json"
)

context = json.loads(
    context_path.read_text()
)


def run_case(decision):
    decision = copy.deepcopy(
        decision
    )

    decision = (
        coordinator
        .enrich_deterministic_configuration(
            decision,
            context,
        )
    )

    errors = (
        coordinator.validate_decision(
            decision,
            context,
        )
    )

    return decision, errors


# ============================================================
# 1. Valid multidimensional ACCEPT
# ============================================================

decision, errors = run_case({
    "decision": "ACCEPT",
    "recommended_threads": 4,
    "recommended_configuration": None,
    "reason": "Regression test.",
    "next_action": "PROMOTE_CANDIDATE",
    "risk": "LOW",
    "evidence_used": [
        "regression_test"
    ],
})

assert errors == [], errors

assert decision[
    "recommended_configuration"
] == {
    "block_size": 64,
    "threads": 4,
}


# ============================================================
# 2. REJECT without operational configuration
# ============================================================

decision, errors = run_case({
    "decision": "REJECT",
    "recommended_threads": None,
    "recommended_configuration": None,
    "reason": "Regression test.",
    "next_action": "REJECT_CANDIDATE",
    "risk": "LOW",
    "evidence_used": [
        "regression_test"
    ],
})

assert errors == [], errors

assert (
    decision[
        "recommended_configuration"
    ]
    is None
)


# ============================================================
# 3. MODIFY without operational configuration
# ============================================================

decision, errors = run_case({
    "decision": "MODIFY",
    "recommended_threads": None,
    "recommended_configuration": None,
    "reason": "Regression test.",
    "next_action": "SEND_TO_CODER",
    "risk": "LOW",
    "evidence_used": [
        "regression_test"
    ],
})

assert errors == [], errors

assert (
    decision[
        "recommended_configuration"
    ]
    is None
)


# ============================================================
# 4. Conflicting ACCEPT must be rejected
# ============================================================

decision, errors = run_case({
    "decision": "ACCEPT",
    "recommended_threads": 10,
    "recommended_configuration": None,
    "reason": "Regression test.",
    "next_action": "PROMOTE_CANDIDATE",
    "risk": "LOW",
    "evidence_used": [
        "regression_test"
    ],
})

assert errors, (
    "Conflicting configuration was "
    "incorrectly accepted."
)

assert (
    "recommended_configuration.threads "
    "must match recommended_threads"
    in errors
)


# Thread-only selection must preserve its measured configuration, too.
context = copy.deepcopy(context)
context["performance"]["selection"]["configuration_dimensions"] = ["threads"]

decision, errors = run_case({
    "decision": "ACCEPT",
    "recommended_threads": 4,
    "recommended_configuration": None,
    "next_action": "PROMOTE_CANDIDATE",
    "risk": "LOW",
})
assert errors == [], errors
assert decision["recommended_configuration"] == {"threads": 4}

decision, errors = run_case({
    "decision": "ACCEPT",
    "recommended_threads": 10,
    "recommended_configuration": None,
    "next_action": "PROMOTE_CANDIDATE",
    "risk": "LOW",
})
assert "recommended_configuration.threads must match recommended_threads" in errors

context["validation"]["correctness_gate"] = "FAIL"
decision, errors = run_case({
    "decision": "ACCEPT",
    "recommended_threads": 4,
    "recommended_configuration": None,
    "next_action": "PROMOTE_CANDIDATE",
    "risk": "LOW",
})
assert "ACCEPT forbidden because correctness did not PASS" in errors


print(
    "================================="
)
print(
    "Coordinator v0.2 regression: PASS"
)
print(
    "7/7 cases behaved as expected."
)
print(
    "================================="
)
