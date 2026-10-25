"""Run backend tests with temporary stores, preserving any running demo's data."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='swarmcfo-tests-') as folder:
    env = dict(os.environ, SWARMCFO_CLAIMS_DIR=str(Path(folder) / 'claims'),
               SWARMCFO_GUIDED_DB=str(Path(folder) / 'guided.sqlite3'))
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                            cwd=root / 'agents', env=env)
raise SystemExit(result.returncode)
