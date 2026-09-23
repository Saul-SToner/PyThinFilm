"""Developer-only full catalog and live transfer/render audit; writes to outputs."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app, APP_ROOT, OUTPUTS_DIR

client = TestClient(app)
rows = []
catalog = client.get('/api/case-library').json()['cases']
materials = client.get('/api/materials').json()
for case in catalog:
    row = {'case_id': case['case_id']}
    try:
        detail = client.get('/api/case-library/' + case['case_id'])
        detail.raise_for_status()
        row['detail'] = 'passed'
        if case['has_live_simulation']:
            response = client.post('/api/simulations', json={'case_id': case['case_id'], 'params': {}, 'export_files': False})
            response.raise_for_status()
            row['simulation'] = 'passed'
            converted = subprocess.run(['node', str(APP_ROOT / 'frontend/tools/audit_case_transfer.cjs')], input=json.dumps({'case': case, 'materials': materials, 'result': response.json()}), text=True, capture_output=True, check=True)
            draft = json.loads(converted.stdout)
            response = client.post('/api/designs/simulate', json={**draft, 'request_id': case['case_id']})
            if response.status_code != 200:
                raise RuntimeError(response.text)
            row['free_design'] = 'passed'
            if draft.get('optiland', {}).get('enabled', True):
                response = client.post('/api/optiland/system', json={'draft': draft}).json()
                if not response.get('ready'):
                    raise RuntimeError(response.get('error'))
                for url in response['artifacts'].values():
                    image = client.get(url)
                    assert image.status_code == 200 and image.content.startswith(b'\x89PNG'), url
                row['optiland'] = 'passed'
                row['template'] = response['system_template']
            else:
                row['optiland'] = 'disabled'
        else:
            row['free_design'] = 'not_supported'
    except Exception as exc:
        row['error'] = str(exc)
    rows.append(row)
    print(json.dumps(row, ensure_ascii=True), flush=True)
report = OUTPUTS_DIR / 'case_runtime_audit.json'
report.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf8')
print(str(report), flush=True)
sys.exit(any('error' in row for row in rows))
