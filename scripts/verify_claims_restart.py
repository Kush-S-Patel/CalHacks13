"""Exercise the real HTTP workflow across two Uvicorn process restarts.

Run from the repository root with .venv/bin/python scripts/verify_claims_restart.py.
Stores are isolated in a temporary directory. No provider API calls are made.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def verify() -> dict:
    with tempfile.TemporaryDirectory(prefix='swarmcfo-restart-') as folder:
        state = Path(folder)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        env = dict(os.environ, SWARMCFO_CLAIMS_DIR=str(state / 'claims'),
                   SWARMCFO_GUIDED_DB=str(state / 'guided.sqlite3'))
        process = None
        log = (state / 'server.log').open('w+')

        def stop():
            nonlocal process
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)
                process = None

        def request(path, body=None):
            data = json.dumps(body).encode() if body is not None else None
            req = Request(base + path, data=data, headers={'Content-Type': 'application/json'})
            with urlopen(req, timeout=15) as response:
                return json.load(response)

        def start():
            nonlocal process
            process = subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(port)],
                cwd=ROOT / 'agents', env=env, stdout=log, stderr=log,
            )
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError('Backend exited: ' + log.read()[-3000:])
                try:
                    request('/health'); return
                except OSError:
                    time.sleep(.15)
            raise RuntimeError('Backend did not become healthy')

        try:
            start()
            result = request('/v1/claims/demo', {'phase': 'start'})
            claim_id = result['claim_id']
            claim_path = '/v1/claims/' + claim_id
            request(claim_path + '/decisions', {'decision': 'exclude', 'reason': 'Staff celebration without program purpose.'})
            for ledger in ['GL-9007', 'GL-9008', 'GL-9009']:
                body = {'action': 'attach_receipt' if ledger == 'GL-9009' else 'exclude',
                        'reason': 'Manager independently reviewed this exception.'}
                if ledger == 'GL-9009':
                    body.update(evidence_id='ev-process-restart', filename='toner-demo.pdf')
                request(claim_path + '/exceptions/' + ledger + '/resolve', body)
            policy = request(claim_path + '/policies', {'reason': 'Carry the correction into future review.'})['policy']['id']
            request('/v1/policies/' + policy + '/approve', {'reason': 'Manager approves the scoped rule.'})
            before = request(claim_path + '/audit')['events']
            stop(); start()
            restored = request(claim_path + '/guided')
            assert restored['phase'] == 'policy_active', restored['phase']
            future = request(claim_path + '/next-period-submissions', {'reason': 'Independently submit October after restart.'})
            assert future['future_claim_work_item']['state'] == 'HELD'
            denied = request(claim_path + '/approval-attempts', {'reason': 'Prove the claims role cannot approve.'})
            assert denied['denied'] is True
            result = request(claim_path + '/approve', {'reason': 'Manager approves the corrected September package.'})
            assert result['phase'] == 'approved'
            assert result['claim']['totals']['eligible_cents'] == 2_813_500
            stop(); start()
            final = request(claim_path + '/guided')
            events = request(claim_path + '/audit')['events']
            assert final['phase'] == 'approved'
            assert final['future_claim']['id'] == future['future_claim']['id']
            ids = {event['id'] for event in events}
            assert {event['id'] for event in before}.issubset(ids)
            assert len(ids) == len(events)
            return {'passed': True, 'real_process_restarts': 2, 'final_phase': final['phase'],
                    'eligible_usd': 28135, 'future_work_state': 'HELD', 'audit_events': len(events),
                    'automated_approval_denied': True, 'provider_calls': False}
        finally:
            stop(); log.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = verify()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
