"""Build an auditable experimental matrix without rerunning or pooling campaigns."""

import argparse
import csv
import json
import math
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis import autotuning_selector, performance_selector
from analysis.artifact_provenance import load_context_evidence, sha256


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Measurement must be finite and positive.")
    return value


def csv_rows(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    if not rows or any(None in row or None in row.values() for row in rows):
        raise ValueError(f"Empty CSV or rows inconsistent with header: {path}")
    return rows


def raw_measurements(path, kind):
    groups = {}
    if kind == "raw_csv":
        records = [(row["mode"], int(row["threads"]), int(row["run"]), row["seconds"])
                   for row in csv_rows(path)]
    else:
        records, current = [], None
        for line in path.read_text().splitlines():
            if line.strip() == "Sequential benchmark:":
                current = ("sequential", 1)
            heading = re.match(r"OpenMP benchmark \((\d+) thread", line)
            if heading:
                current = ("openmp", int(heading[1]))
            direct = re.match(r"(SEQ|\d+T) Run=(\d+) Time=(\S+?)(ms|s)$", line.strip())
            gate = re.match(r"Run (\d+): (\S+) s$", line.strip())
            if direct:
                mode, threads = ("sequential", 1) if direct[1] == "SEQ" else ("openmp", int(direct[1][:-1]))
                records.append((mode, threads, int(direct[2]), float(direct[3]) / (1000 if direct[4] == "ms" else 1)))
            elif gate and current:
                records.append((*current, int(gate[1]), gate[2]))
    for mode, threads, run, seconds in records:
        if mode not in ("sequential", "openmp") or threads < 1 or run < 1:
            raise ValueError("Invalid raw measurement identity.")
        group = groups.setdefault((mode, threads), {})
        if run in group:
            raise ValueError("Duplicate run: log may combine multiple campaigns.")
        group[run] = positive(seconds)
    if not groups:
        raise ValueError(f"No raw measurements in {path}")
    if any(set(runs) != set(range(1, len(runs) + 1)) for runs in groups.values()):
        raise ValueError("Raw run identifiers have gaps.")
    return [{"mode": mode, "threads": threads, "samples": [runs[index] for index in sorted(runs)],
             "median_seconds": statistics.median(runs.values()), "mean_seconds": statistics.mean(runs.values())}
            for (mode, threads), runs in groups.items()]


def normalize(rows):
    rows = [dict(row) for row in rows]
    sequential = [row for row in rows if row["mode"] == "sequential"]
    if len(sequential) != 1 or sequential[0]["threads"] != 1:
        raise ValueError("Exactly one sequential baseline per campaign is required.")
    keys = set()
    for row in rows:
        if row["mode"] not in ("sequential", "openmp") or type(row["threads"]) is not int or row["threads"] < 1:
            raise ValueError("Invalid mode or thread count.")
        if "block_size" in row and (type(row["block_size"]) is not int or row["block_size"] < 1):
            raise ValueError("Block size must be a positive integer.")
        key = (row["mode"], row.get("block_size"), row["threads"])
        if key in keys:
            raise ValueError("Repeated configuration: select one campaign, not an accumulated CSV.")
        keys.add(key)
        for field in ("median_seconds", "mean_seconds"):
            row[field] = positive(row[field])
        samples = row.get("samples")
        row["sample_count"] = len(samples) if samples else None
        if samples:
            samples = [positive(value) for value in samples]
            row.update(std_dev_seconds=statistics.pstdev(samples), min_seconds=min(samples), max_seconds=max(samples))
        row["speedup"] = sequential[0]["median_seconds"] / row["median_seconds"]
        row["efficiency"] = row["speedup"] / row["threads"]
    if not any(row["mode"] == "openmp" for row in rows):
        raise ValueError("Campaign has no OpenMP configurations.")
    for row in rows:
        one = next((other for other in rows if other["mode"] == "openmp" and other["threads"] == 1
                    and other.get("block_size") == row.get("block_size")), None)
        row["parallel_scaling_speedup"] = one["median_seconds"] / row["median_seconds"] if one and row["mode"] == "openmp" else None
        row["parallel_scaling_efficiency"] = row["parallel_scaling_speedup"] / row["threads"] if row["parallel_scaling_speedup"] else None
    return sorted(rows, key=lambda row: (row["mode"] != "sequential", row.get("block_size") or 0, row["threads"]))


def load_campaign(spec, root):
    path = root / spec["source"]
    kind = spec["format"]
    evidence_status, recorded_provenance = "HISTORICAL_UNBOUND", None
    if kind in ("harness_log", "gate_log", "raw_csv"):
        rows = raw_measurements(path, kind)
    elif kind == "evaluation_case":
        archived = json.loads(path.read_text())
        case = next(case for case in archived["cases"] if case["case"] == spec["case"])
        rows = case["measurements"]
        try:
            _, bundle, reference = load_context_evidence(Path(case["context"]["path"]))
        except FileNotFoundError:
            evidence_status = "ARCHIVED_SUMMARY_ONLY"
        else:
            if reference != case["context"] or bundle["measurements"] != rows:
                raise ValueError("Archived case disagrees with its bound evidence.")
            rows = [dict(row, samples=measurement["times"]) for row, measurement
                    in zip(rows, bundle["performance"]["measurements"])]
            evidence_status = "VERIFIED_LOCAL_GATES"
            recorded_provenance = bundle["performance"]["provenance"]
    elif kind == "autotuning_csv":
        data = csv_rows(path)
        if len({(row["timestamp"], row["n"], row["sequential_median_ms"]) for row in data}) != 1:
            raise ValueError("Select exactly one autotuning campaign.")
        sequential = positive(data[0]["sequential_median_ms"]) / 1000
        rows = [{"mode": "sequential", "threads": 1, "median_seconds": sequential, "mean_seconds": sequential}]
        for row in data:
            error = float(row["max_absolute_error"])
            if not math.isfinite(error) or error < 0:
                raise ValueError("Invalid recorded correctness error.")
            rows.append({"mode": "openmp", "threads": int(row["threads"]), "block_size": int(row["block_size"]),
                         "median_seconds": positive(row["median_ms"]) / 1000,
                         "mean_seconds": positive(row["mean_ms"]) / 1000,
                         "std_dev_seconds": float(row["std_dev_ms"]) / 1000,
                         "min_seconds": positive(row["min_ms"]) / 1000,
                         "max_seconds": positive(row["max_ms"]) / 1000,
                         "max_absolute_error": error})
    else:
        data = csv_rows(path)
        if spec.get("timestamp"):
            data = [row for row in data if row.get("timestamp") == spec["timestamp"]]
        if not data:
            raise ValueError("Requested campaign timestamp not found.")
        rows = [{"mode": row.get("mode", row.get("version")), "threads": int(row["threads"]),
                 "median_seconds": positive(row["median_seconds"]), "mean_seconds": positive(row["mean_seconds"])} for row in data]
        if spec.get("raw_source"):
            raw = raw_measurements(root / spec["raw_source"], spec.get("raw_format", "harness_log"))
            if {(row["mode"], row["threads"]) for row in raw} != {(row["mode"], row["threads"]) for row in rows}:
                raise ValueError("Raw and summary configurations disagree.")
            for row in rows:
                samples = next(item for item in raw if (item["mode"], item["threads"]) == (row["mode"], row["threads"]))
                for field in ("median_seconds", "mean_seconds"):
                    if not math.isclose(samples[field], row[field], rel_tol=1e-8, abs_tol=5.1e-7):
                        raise ValueError("Raw samples disagree with normalized CSV.")
                row["samples"] = samples["samples"]
    rows = normalize(rows)
    if kind == "autotuning_csv":
        selection = autotuning_selector.select_configuration({"results": [row for row in rows if row["mode"] == "openmp"],
                                                              "sequential_median_seconds": rows[0]["median_seconds"],
                                                              "n": int(data[0]["n"])})
    else:
        selection = performance_selector.select_configuration(rows)
    recommended = selection.get("recommended")
    selected = next((row for row in rows if recommended and row["mode"] == "openmp"
                     and row["threads"] == recommended["threads"] and row.get("block_size") == recommended.get("block_size")), None)
    return rows, selection, selected, evidence_status, recorded_provenance


def inventory(root, excluded):
    records, seen = [], {}
    for path in sorted((root / "results").rglob("*.csv")):
        if path.is_relative_to(excluded) or path.is_relative_to(root / "results/consolidated"):
            continue
        relative = path.relative_to(root).as_posix()
        digest = sha256(path.read_bytes())
        issues = []
        with path.open(newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader, [])
            data = list(reader)
        malformed = [index for index, row in enumerate(data, 2) if len(row) != len(header)]
        if malformed:
            issues.append("HEADER_MISMATCH lines " + ",".join(map(str, malformed)))
        modes = "mode" if "mode" in header else "version" if "version" in header else None
        baselines = [index for index, row in enumerate(data, 2) if modes and len(row) == len(header)
                     and row[header.index(modes)] == "sequential"]
        if len(baselines) > 1 and "run" not in header:
            issues.append("MULTIPLE_BASELINES lines " + ",".join(map(str, baselines)))
        if "threads" in header and ("median_seconds" in header or "median_ms" in header) and "run" not in header:
            keys, repeated = set(), []
            for index, row in enumerate(data, 2):
                if len(row) != len(header):
                    continue
                key = tuple(row[header.index(field)] for field in (modes, "block_size", "threads") if field in header)
                if key in keys:
                    repeated.append(index)
                keys.add(key)
            if repeated:
                issues.append("REPEATED_CONFIGURATIONS lines " + ",".join(map(str, repeated)))
        if modes:
            bad_modes = [index for index, row in enumerate(data, 2) if len(row) == len(header)
                         and row[header.index(modes)] not in ("sequential", "openmp")]
            if bad_modes:
                issues.append("INVALID_MODE lines " + ",".join(map(str, bad_modes)))
        records.append({"path": relative, "sha256": digest, "rows": len(data), "columns": header,
                        "duplicate_of": seen.get(digest), "issues": issues})
        seen.setdefault(digest, relative)
    return records


def write_csv(path, rows, columns):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def consolidate(catalog, root):
    campaigns = []
    for spec in catalog["campaigns"]:
        rows, selection, selected, evidence_status, provenance = load_campaign(spec, root)
        missing = list(spec.get("limitations", []))
        if evidence_status != "VERIFIED_LOCAL_GATES":
            missing += ["sem vínculo histórico entre hashes de fontes, corretude e medições",
                        "flags/entrada da receita atual não atestam a compilação histórica"]
        if any(row["sample_count"] is None for row in rows if row["mode"] == "openmp"):
            missing.append("amostras individuais indisponíveis para parte das configurações")
        if selected and selected["parallel_scaling_speedup"] is None:
            missing.append("sem OpenMP 1T da mesma variante para calcular escalabilidade")
        references = []
        paths = {spec["source"], spec["candidate"], catalog["recipes"][spec["recipe"]]["source"]}
        for field in ("original", "benchmark_driver", "raw_source", "correctness_source"):
            if spec.get(field):
                paths.add(spec[field])
        environment = catalog["environments"][spec["environment"]]
        if environment.get("source"):
            paths.add(environment["source"])
        for name in sorted(paths):
            path = root / name
            references.append({"path": name, "sha256_now": sha256(path.read_bytes()) if path.is_file() else None})
            if not path.is_file():
                missing.append("referência indisponível: " + name)
        campaigns.append({**spec, "hardware": environment["hardware"], "compiler": environment["compiler"],
                          "evidence_status": evidence_status, "missing": missing,
                          "recorded_provenance": provenance,
                          "references": references, "measurements": rows,
                          "selection": selection, "selected": selected})
    return campaigns


def plot_campaigns(campaigns, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    generated = []
    for environment in sorted({case["environment"] for case in campaigns}):
        cases = [case for case in campaigns if case["environment"] == environment]
        figure, axes = plt.subplots(math.ceil(len(cases) / 2), 2, figsize=(11, 3.3 * math.ceil(len(cases) / 2)), squeeze=False)
        for axis, case in zip(axes.flat, cases):
            selected = case["selected"]
            block = selected.get("block_size") if selected else None
            rows = [row for row in case["measurements"] if row["mode"] == "openmp" and row.get("block_size") == block]
            axis.plot([row["threads"] for row in rows], [row["speedup"] for row in rows], "o-", label="vs. sequencial")
            if all(row["parallel_scaling_speedup"] is not None for row in rows):
                axis.plot([row["threads"] for row in rows], [row["parallel_scaling_speedup"] for row in rows], "s--", label="vs. OpenMP 1T (mesma variante)")
            axis.axhline(1, color="grey", linewidth=0.7)
            axis.set(title=case["id"] + (f" / bloco {block}" if block else ""), xlabel="Threads", ylabel="Razão dos tempos medianos")
            axis.set_xticks([row["threads"] for row in rows])
            axis.grid(alpha=0.2)
            axis.legend(fontsize=8)
        for axis in list(axes.flat)[len(cases):]:
            axis.set_visible(False)
        figure.suptitle(cases[0]["hardware"] + " — campanhas separadas; sem agrupamento de amostras", fontsize=11)
        figure.tight_layout(rect=(0, 0, 1, 0.96))
        for extension in ("svg", "pdf", "png"):
            name = f"scaling_{environment}.{extension}"
            figure.savefig(output / name, dpi=150)
            generated.append(name)
        plt.close(figure)
    return {"library": "matplotlib", "version": matplotlib.__version__, "files": generated}


def write_outputs(catalog, campaigns, files, output, plots):
    matrix, curves, samples = [], [], []
    for case in campaigns:
        selected = case["selected"]
        one = next((row for row in case["measurements"] if row["mode"] == "openmp" and row["threads"] == 1
                    and selected and row.get("block_size") == selected.get("block_size")), None)
        matrix.append({"campaign": case["id"], "kernel": case["kernel"], "pattern": case["pattern"],
                       "hardware": case["hardware"], "variant_origin": case["origin"],
                       "candidate": case["candidate"], "original_recipe": case.get("original"), "compiler": case["compiler"],
                       "recorded_candidate_sha256": case["recorded_provenance"]["inputs"]["candidate"]["sha256"] if case["recorded_provenance"] else None,
                       "flags_recipe": catalog["recipes"][case["recipe"]]["flags"], "input_recipe": case["input"],
                       "correctness_record": case["correctness"], "evidence_status": case["evidence_status"],
                       "sample_counts": ",".join(map(str, sorted({row["sample_count"] for row in case["measurements"] if row["sample_count"]}))) or "unknown",
                       "sequential_seconds": case["measurements"][0]["median_seconds"],
                       "selected_threads": selected["threads"] if selected else None,
                       "selected_block_size": selected.get("block_size") if selected else None,
                       "selected_seconds": selected["median_seconds"] if selected else None,
                       "speedup_vs_sequential": selected["speedup"] if selected else None,
                       "transformation_speedup_same_variant": case["measurements"][0]["median_seconds"] / one["median_seconds"] if one else None,
                       "parallel_scaling_speedup": selected["parallel_scaling_speedup"] if selected else None,
                       "parallel_scaling_efficiency": selected["parallel_scaling_efficiency"] if selected else None,
                       "selector_status": case["selection"].get("parallel_status", case["selection"]["status"]),
                       "missing": "; ".join(case["missing"]), "source": case["source"]})
        for row in case["measurements"]:
            curves.append({"campaign": case["id"], **row})
            for index, seconds in enumerate(row.get("samples", []), 1):
                samples.append({"campaign": case["id"], "mode": row["mode"], "threads": row["threads"],
                                "block_size": row.get("block_size"), "run": index, "seconds": seconds})
    write_csv(output / "matrix.csv", matrix, list(matrix[0]))
    write_csv(output / "measurements.csv", curves, ("campaign", "mode", "threads", "block_size", "median_seconds", "mean_seconds",
              "sample_count", "std_dev_seconds", "min_seconds", "max_seconds", "speedup", "parallel_scaling_speedup", "parallel_scaling_efficiency"))
    write_csv(output / "samples.csv", samples, ("campaign", "mode", "threads", "block_size", "run", "seconds"))
    report = {"schema": "tcc2-experiment-consolidation", "version": "0.1",
              "generator_sha256": sha256(Path(__file__).read_bytes()),
              "catalog_sha256": sha256(json.dumps(catalog, sort_keys=True).encode()),
              "campaigns": campaigns, "inventory": files, "plots": plots}
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    lines = ["# Item 5 — matriz experimental consolidada", "",
             "Campanhas históricas e gates locais permanecem separados. Seleção analítica não é promoção.",
             "Flags e tamanhos rotulados como receita precisam de confirmação nas campanhas históricas.", "",
             "| Campanha | Hardware | Origem | Configuração selecionada | Tempo (s) | vs. seq. | Escalabilidade 1T | Eficiência paralela | Evidência |",
             "|---|---|---|---|---:|---:|---:|---:|---|"]
    def number(value):
        return f"{value:.4g}" if value is not None else "—"
    for row in matrix:
        config = str(row["selected_threads"]) + "T" if row["selected_threads"] else "sem recomendação"
        if row["selected_block_size"]:
            config += f" / bloco {row['selected_block_size']}"
        lines.append(f"| {row['campaign']} | {row['hardware']} | {row['variant_origin']} | {config} | "
                     f"{number(row['selected_seconds'])} | {number(row['speedup_vs_sequential'])} | "
                     f"{number(row['parallel_scaling_speedup'])} | {number(row['parallel_scaling_efficiency'])} | {row['evidence_status']} |")
    lines += ["", "## Lacunas por campanha", ""]
    for case in campaigns:
        lines.append(f"- **{case['id']}**: " + ("; ".join(case["missing"]) or "gates locais verificados; validação restrita ao driver fornecido") + ".")
    lines += ["", "## Inventário dos CSVs", "", "| Arquivo | Linhas | Duplicado de | Inconsistências |", "|---|---:|---|---|"]
    for item in files:
        lines.append(f"| {item['path']} | {item['rows']} | {item['duplicate_of'] or '—'} | {'; '.join(item['issues']) or '—'} |")
    lines += ["", "## Gráficos", ""]
    for filename in plots.get("files", []):
        if filename.endswith(".svg"):
            lines.append(f"![{filename}]({filename})")
    lines += ["", "Gráficos exibem razões de medianas, sem intervalos de confiança.",
              "Dispersão e amostras recuperadas estão em measurements.csv e samples.csv; não se agrupam campanhas.",
              "Hashes sha256_now identificam os arquivos disponíveis hoje, sem atestar os bytes compilados historicamente.",
              "O resultado negativo (sem ganho) também é mantido. Nenhuma medição de LLM simulada entra nesta matriz."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "docs/experiment_catalog.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/consolidated")
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    try:
        catalog = json.loads(args.catalog.read_text())
        if not catalog["campaigns"] or len({case["id"] for case in catalog["campaigns"]}) != len(catalog["campaigns"]):
            raise ValueError("Campaign identifiers must be nonempty and unique.")
        output = args.output_dir.resolve()
        # Refuse to turn a results directory containing source evidence into an output target.
        allowed = {"matrix.csv", "measurements.csv", "samples.csv", "report.json", "REPORT.md"}
        allowed.update(f"scaling_{environment}.{extension}" for environment in catalog["environments"]
                       for extension in ("svg", "pdf", "png"))
        if output.exists() and any(path.is_symlink() or not path.is_file() or path.name not in allowed for path in output.iterdir()):
            raise ValueError("Output directory contains files outside this report.")
        if any((ROOT / case["source"]).resolve().is_relative_to(output) for case in catalog["campaigns"]):
            raise ValueError("Output would overwrite source evidence.")
        campaigns = consolidate(catalog, ROOT)
        files = inventory(ROOT, output)
        output.mkdir(parents=True, exist_ok=True)
        plots = {"files": []} if args.no_plots else plot_campaigns(campaigns, output)
        write_outputs(catalog, campaigns, files, output, plots)
    except (OSError, ValueError, KeyError, StopIteration, RuntimeError, ImportError) as error:
        print(f"CONSOLIDATION_FAILED: {error}")
        return 1
    print(f"CONSOLIDATED: {len(campaigns)} campaigns, {len(files)} CSV files; {output / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
