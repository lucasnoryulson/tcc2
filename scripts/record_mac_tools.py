"""Archive actual profiler availability, hardware and power observations."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_scaling import Campaign, write_json


def record(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'logs').mkdir()
    campaign = Campaign(output, 30)
    commands = [['/usr/sbin/sysctl', 'hw.model', 'hw.memsize', 'hw.physicalcpu', 'hw.logicalcpu',
                 'hw.perflevel0.physicalcpu', 'hw.perflevel1.physicalcpu', 'machdep.cpu.brand_string'],
                ['xcode-select', '-p'], ['xcrun', 'xctrace', 'list', 'templates'],
                ['sw_vers'], ['pmset', '-g', 'batt'], ['pmset', '-g', 'therm'],
                ['ollama', '--version']]
    observations = []
    for command in commands:
        stdout, stderr, invocation = campaign.run(command, check=False)
        observations.append(dict(command=command, invocation=invocation, stdout=stdout, stderr=stderr.decode(errors='replace')))
    write_json(output / 'report.json', dict(recorded_utc=datetime.now(timezone.utc).isoformat(), observations=observations,
        caveat='Availability and point-in-time observations; no thermal/frequency control or hardware-counter measurement'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    record(parser.parse_args().output)
