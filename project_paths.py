"""Portable input locations and per-run output paths shared by both methods."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parent
_DEFAULT_RUN_ID = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S_%f_utc')
_METHODS = {'salt_dilution', 'fluvial_seismology'}


def method_path(method, relative):
    """Resolve an input path against the method directory, independent of cwd."""
    if method not in _METHODS:
        raise ValueError(f'Unknown method: {method}')
    return str(ROOT / method / relative)


def result_path(method, relative):
    """Create an output's parent directories within one named analysis run.

    Set MORA_RUN_ID before starting Python to choose a descriptive run name.
    The initial run record describes a started run, not a successful analysis.
    """
    if method not in _METHODS:
        raise ValueError(f'Unknown method: {method}')
    run_id = os.environ.get('MORA_RUN_ID', _DEFAULT_RUN_ID)
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]*', run_id):
        raise ValueError('MORA_RUN_ID must use lowercase letters, digits, underscores, dots, or hyphens.')
    run_root = (ROOT / method / 'results' / run_id).resolve()
    output = (run_root / relative).resolve()
    if not output.is_relative_to(run_root):
        raise ValueError('Result paths must stay inside the analysis run directory.')
    output.parent.mkdir(parents=True, exist_ok=True)
    info = run_root / 'run_info.json'
    if not info.exists():
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
        info.write_text(json.dumps({
            'analysis_id': run_id, 'method': method, 'status': 'started',
            'started_at_utc': datetime.now(timezone.utc).isoformat(),
            'git_commit': commit.stdout.strip() if commit.returncode == 0 else None,
            'inputs': [], 'config_file': None, 'notes': '',
        }, indent=2) + '\n')
    return str(output)
