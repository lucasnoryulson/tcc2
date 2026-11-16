"""Optional real subprocess timings, separate from correctness/performance evidence."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time


def run_timed(command, *, origin, **kwargs):
    destination = os.environ.get('TCC2_PROCESS_TIMING_LOG')
    if not destination:
        return subprocess.run(command, **kwargs)
    started = time.perf_counter()
    record = dict(origin=origin, command=list(map(str, command)),
                  kind='compilation' if '-o' in command else 'execution',
                  stage=os.environ.get('TCC2_TIMING_STAGE', 'promotion'),
                  started_utc=datetime.now(timezone.utc).isoformat())
    try:
        result = subprocess.run(command, **kwargs)
        record['returncode'] = result.returncode
        return result
    except BaseException as error:
        record.update(returncode=None, error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        record['wall_seconds'] = time.perf_counter() - started
        with Path(destination).open('a') as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
