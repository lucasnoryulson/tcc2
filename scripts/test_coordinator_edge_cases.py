import copy
import importlib.util
import json
from pathlib import Path


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


context_path = Path(
    "results/mac_m5_2026-09-09/"
    "agents/wavefront_tiled_agent_context.json"
)

context = json.loads(
    context_path.read_text()
)


tests = {
    "ACCEPT_GOOD": {
        "decision": "ACCEPT",
        "recommended_threads": 4,
        "recommended_configuration": None,
        "reason": "Synthetic test.",
        "next_action": "PROMOTE_CANDIDATE",
        "risk": "LOW",
        "evidence_used": [
            "synthetic_test"
        ],
    },

    "REJECT_NULL_THREADS": {
        "decision": "REJECT",
        "recommended_threads": None,
        "recommended_configuration": None,
        "reason": "Synthetic test.",
        "next_action": "REJECT_CANDIDATE",
        "risk": "LOW",
        "evidence_used": [
            "synthetic_test"
        ],
    },

    "MODIFY_NULL_THREADS": {
        "decision": "MODIFY",
        "recommended_threads": None,
        "recommended_configuration": None,
        "reason": "Synthetic test.",
        "next_action": "SEND_TO_CODER",
        "risk": "LOW",
        "evidence_used": [
            "synthetic_test"
        ],
    },

    "ACCEPT_CONFLICT": {
        "decision": "ACCEPT",
        "recommended_threads": 10,
        "recommended_configuration": None,
        "reason": "Synthetic test.",
        "next_action": "PROMOTE_CANDIDATE",
        "risk": "LOW",
        "evidence_used": [
            "synthetic_test"
        ],
    },
}


print(
    "===== COORDINATOR v0.2 EDGE TESTS ====="
)


for name, original in tests.items():

    decision = copy.deepcopy(
        original
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

    print()
    print(
        "-------------------------------------"
    )
    print(name)
    print(
        "-------------------------------------"
    )

    print(
        "Decision:",
        decision["decision"],
    )

    print(
        "Recommended threads:",
        decision[
            "recommended_threads"
        ],
    )

    print(
        "Recommended configuration:",
        decision.get(
            "recommended_configuration"
        ),
    )

    print(
        "Validation:",
        "PASS"
        if not errors
        else "FAIL",
    )

    if errors:

        for error in errors:

            print(
                "  -",
                error,
            )
