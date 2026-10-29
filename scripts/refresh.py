#!/usr/bin/env python3
"""Refresh GitHub metadata for the curated catalog. Requires authenticated gh CLI."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'data' / 'catalog.json'
data = json.loads(path.read_text())
for project in data['projects']:
    result = subprocess.run(['gh', 'api', 'repos/' + project['id']], capture_output=True, text=True, check=True)
    repo = json.loads(result.stdout)
    license_id = (repo.get('license') or {}).get('spdx_id')
    project.update(id=repo['full_name'], url=repo['html_url'], language=repo.get('language') or 'Not specified',
                   license=license_id if license_id and license_id != 'NOASSERTION' else 'See repository',
                   stars=repo['stargazers_count'], updated=(repo.get('pushed_at') or '')[:10] or None)
data['snapshot'] = datetime.now(timezone.utc).date().isoformat()
path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
print(f"Refreshed {len(data['projects'])} projects on {data['snapshot']}")
