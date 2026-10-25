"""Create/update a private Apify Actor from the reviewed local source and build it.

Reads credentials from the ignored root .env. Never publishes to Apify Store.
"""
from pathlib import Path
import json
import httpx
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[1]
config = dotenv_values(ROOT / '.env')
token = config.get('APIFY_TOKEN')
if not token:
    raise SystemExit('Configure APIFY_TOKEN in the ignored root .env first.')
source = ROOT / 'integrations/grant-rule-watcher'
files = [
    {'name': name, 'format': 'TEXT', 'content': (source / name).read_text()}
    for name in ['Dockerfile', 'package.json', 'src/main.js', '.actor/actor.json']
]
version = {'versionNumber': '1.0', 'sourceType': 'SOURCE_FILES', 'buildTag': 'latest', 'sourceFiles': files}
with httpx.Client(base_url='https://api.apify.com/v2', headers={'Authorization': 'Bearer ' + token}, timeout=60) as client:
    response = client.get('/actors', params={'limit': 100})
    response.raise_for_status()
    actor = next((item for item in response.json()['data']['items'] if item['name'] == 'swarmcfo-grant-rule-watcher'), None)
    if actor is None:
        response = client.post('/actors', json={
            'name': 'swarmcfo-grant-rule-watcher', 'title': 'SwarmCFO Grant Rule Watcher',
            'isPublic': False, 'versions': [version],
            'defaultRunOptions': {'build': 'latest', 'memoryMbytes': 256, 'timeoutSecs': 90},
        })
    else:
        response = client.put('/actors/' + actor['id'] + '/versions/1.0', json=version)
    response.raise_for_status()
    if actor is None:
        actor = response.json()['data']
    actor_id = actor['id']
    set_key(str(ROOT / '.env'), 'APIFY_ACTOR_ID', actor_id)
    response = client.post('/actors/' + actor_id + '/builds', params={'version': '1.0', 'tag': 'latest', 'waitForFinish': 30})
    response.raise_for_status()
    build = response.json()['data']
    report = {'actor_id': actor_id, 'private': True, 'build_id': build['id'], 'status': build['status']}
    receipt_dir = ROOT / 'data/erp_vault'
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / 'apify-build-receipt.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
