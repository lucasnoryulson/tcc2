#!/usr/bin/env python3

import argparse
import json
import re
from collections import Counter
from pathlib import Path


VERSION = "0.2"

REPO_ROOT = Path(
    __file__
).resolve().parents[1]

LOCATION_RE = re.compile(
    r"^(.*?):(\d+):(\d+):\s+remark:\s+(.*)$"
)


def classify_message(message):
    text = message.lower()

    if (
        "unsafe dependent memory operations" in text
        or "unknown dependence" in text
    ):
        return {
            "event":
                "VECTORIZATION_BLOCKED_MEMORY_DEPENDENCE",
            "candidate_strategies": [
                "SCALAR_ACCUMULATOR",
                "LOOP_RESTRUCTURE",
            ],
        }

    if (
        "cost-model indicates that vectorization "
        "is not beneficial" in text
    ):
        return {
            "event":
                "VECTORIZATION_REJECTED_BY_COST_MODEL",
            "candidate_strategies": [
                "EXPLICIT_SIMD_TRIAL",
            ],
        }

    if (
        "vectorized loop" in text
        and "not vectorized" not in text
    ):
        return {
            "event":
                "VECTORIZATION_APPLIED",
            "candidate_strategies": [],
        }

    if "interleaved loop" in text:
        return {
            "event":
                "INTERLEAVING_APPLIED",
            "candidate_strategies": [],
        }

    if (
        "control flow cannot be substituted "
        "for a select" in text
    ):
        return {
            "event":
                "VECTORIZATION_BLOCKED_CONTROL_FLOW",
            "candidate_strategies": [
                "IF_CONVERSION",
                "LOOP_RESTRUCTURE",
            ],
        }

    if (
        "call instruction cannot be vectorized"
        in text
    ):
        return {
            "event":
                "VECTORIZATION_BLOCKED_CALL",
            "candidate_strategies": [
                "INLINE_OR_REWRITE_CALL",
            ],
        }

    if "loop not vectorized" in text:
        return {
            "event":
                "VECTORIZATION_NOT_APPLIED",
            "candidate_strategies": [],
        }

    return None


def parse_diagnostics(text):
    records = []

    for raw_line in text.splitlines():
        match = LOCATION_RE.match(
            raw_line.strip()
        )

        if not match:
            continue

        records.append({
            "source": match.group(1),
            "line": int(match.group(2)),
            "column": int(match.group(3)),
            "message": match.group(4),
        })

    return records


def resolve_source_path(source):
    source_path = Path(source)

    candidates = []

    if source_path.is_absolute():
        candidates.append(source_path)

    candidates.append(
        Path.cwd() / source_path
    )

    candidates.append(
        REPO_ROOT / source_path
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    return None


def find_matching_brace(text, open_pos):
    depth = 0

    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    escaped = False

    i = open_pos

    while i < len(text):
        char = text[i]

        next_char = (
            text[i + 1]
            if i + 1 < len(text)
            else ""
        )

        if in_line_comment:
            if char == "\n":
                in_line_comment = False

            i += 1
            continue

        if in_block_comment:
            if (
                char == "*"
                and next_char == "/"
            ):
                in_block_comment = False
                i += 2
                continue

            i += 1
            continue

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False

            i += 1
            continue

        if in_char:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                in_char = False

            i += 1
            continue

        if (
            char == "/"
            and next_char == "/"
        ):
            in_line_comment = True
            i += 2
            continue

        if (
            char == "/"
            and next_char == "*"
        ):
            in_block_comment = True
            i += 2
            continue

        if char == '"':
            in_string = True
            i += 1
            continue

        if char == "'":
            in_char = True
            i += 1
            continue

        if char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return i

        i += 1

    return None


def discover_function_range(
    source_path,
    function_name,
):
    text = source_path.read_text(
        errors="replace"
    )

    pattern = re.compile(
        rf"\b{re.escape(function_name)}\s*\("
    )

    for match in pattern.finditer(text):
        brace_pos = text.find(
            "{",
            match.end(),
        )

        if brace_pos == -1:
            continue

        between = text[
            match.end():brace_pos
        ]

        # Skip prototypes.
        if ";" in between:
            continue

        end_pos = find_matching_brace(
            text,
            brace_pos,
        )

        if end_pos is None:
            continue

        start_line = (
            text.count(
                "\n",
                0,
                match.start(),
            )
            + 1
        )

        end_line = (
            text.count(
                "\n",
                0,
                end_pos,
            )
            + 1
        )

        return {
            "start": start_line,
            "end": end_line,
        }

    return None


def filter_by_function(
    records,
    function_name,
):
    range_cache = {}
    source_ranges = []
    selected = []

    for record in records:
        source = record["source"]

        if source not in range_cache:
            resolved = resolve_source_path(
                source
            )

            if resolved is None:
                range_cache[source] = None
                continue

            function_range = (
                discover_function_range(
                    resolved,
                    function_name,
                )
            )

            if function_range is None:
                range_cache[source] = None
                continue

            range_cache[source] = {
                "resolved_source":
                    str(resolved),
                "start":
                    function_range["start"],
                "end":
                    function_range["end"],
            }

            source_ranges.append({
                "diagnostic_source":
                    source,
                "resolved_source":
                    str(resolved),
                "start":
                    function_range["start"],
                "end":
                    function_range["end"],
            })

        current_range = (
            range_cache[source]
        )

        if current_range is None:
            continue

        if (
            current_range["start"]
            <= record["line"]
            <= current_range["end"]
        ):
            selected.append(record)

    if not source_ranges:
        raise RuntimeError(
            f"Function '{function_name}' "
            "was not found in any source "
            "referenced by the diagnostic log."
        )

    return (
        selected,
        source_ranges,
    )


def classify_records(records):
    events = []

    for record in records:
        classification = classify_message(
            record["message"]
        )

        if classification is None:
            continue

        events.append({
            "source":
                record["source"],
            "line":
                record["line"],
            "column":
                record["column"],
            "event":
                classification["event"],
            "message":
                record["message"],
            "candidate_strategies":
                classification[
                    "candidate_strategies"
                ],
        })

    return events


def build_strategy_queue(events):
    queue = []

    for event in events:
        for strategy in event[
            "candidate_strategies"
        ]:
            if strategy not in queue:
                queue.append(strategy)

    return queue


def choose_dominant_event(events):
    priority = [
        "VECTORIZATION_BLOCKED_MEMORY_DEPENDENCE",
        "VECTORIZATION_REJECTED_BY_COST_MODEL",
        "VECTORIZATION_BLOCKED_CONTROL_FLOW",
        "VECTORIZATION_BLOCKED_CALL",
        "VECTORIZATION_NOT_APPLIED",
        "VECTORIZATION_APPLIED",
        "INTERLEAVING_APPLIED",
    ]

    present = {
        event["event"]
        for event in events
    }

    for candidate in priority:
        if candidate in present:
            return candidate

    return None


def analyze_file(
    path,
    line_start=None,
    line_end=None,
    function_name=None,
):
    if (
        function_name is not None
        and (
            line_start is not None
            or line_end is not None
        )
    ):
        raise ValueError(
            "Use either --function or "
            "--line-start/--line-end, "
            "not both."
        )

    path = Path(path)

    text = path.read_text(
        errors="replace"
    )

    records = parse_diagnostics(
        text
    )

    source_ranges = []

    if function_name is not None:
        records, source_ranges = (
            filter_by_function(
                records,
                function_name,
            )
        )

        filter_mode = "function"

    elif (
        line_start is not None
        or line_end is not None
    ):
        filtered = []

        for record in records:
            if (
                line_start is not None
                and record["line"]
                    < line_start
            ):
                continue

            if (
                line_end is not None
                and record["line"]
                    > line_end
            ):
                continue

            filtered.append(record)

        records = filtered
        filter_mode = "line_range"

    else:
        filter_mode = "none"

    events = classify_records(
        records
    )

    counts = Counter(
        event["event"]
        for event in events
    )

    return {
        "version": VERSION,
        "source_log": str(path),
        "filter_mode": filter_mode,
        "function_filter": (
            {
                "name": function_name,
                "source_ranges":
                    source_ranges,
            }
            if function_name
            else None
        ),
        "line_filter": {
            "start": line_start,
            "end": line_end,
        },
        "dominant_event":
            choose_dominant_event(
                events
            ),
        "event_counts":
            dict(counts),
        "candidate_strategy_queue":
            build_strategy_queue(
                events
            ),
        "events": events,
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert compiler optimization "
            "remarks into structured feedback."
        )
    )

    parser.add_argument(
        "input",
        help="Compiler diagnostic log.",
    )

    parser.add_argument(
        "--function",
        default=None,
        help=(
            "Automatically restrict remarks "
            "to this function."
        ),
    )

    parser.add_argument(
        "--line-start",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--line-end",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path.",
    )

    args = parser.parse_args()

    result = analyze_file(
        args.input,
        line_start=args.line_start,
        line_end=args.line_end,
        function_name=args.function,
    )

    rendered = json.dumps(
        result,
        indent=2,
    )

    print(rendered)

    if args.output:
        output = Path(
            args.output
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            rendered + "\n"
        )


if __name__ == "__main__":
    main()
