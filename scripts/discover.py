#!/usr/bin/env python3
"""Gather GitHub search candidates for human review; never writes to the catalog."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
QUERIES = ['topic:aerodynamics', 'topic:aerospace-engineering', 'topic:aircraft-design',
           'topic:rocket-propulsion', 'topic:turbomachinery', 'topic:computational-fluid-dynamics',
           'topic:flight-dynamics', 'topic:astrodynamics', 'topic:finite-element-analysis']
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pages', type=int, default=1, choices=range(1, 11), help='Pages per query (1–10; GitHub search caps results at 1000)')
parser.add_argument('--output', default='candidates.json', help='Review queue output (not the catalog)')
args = parser.parse_args()
catalog = json.loads((ROOT / 'data/catalog.json').read_text())
known = {p['id'].lower() for p in catalog['projects']}
candidates = {}
for query in QUERIES:
    for page in range(1, args.pages + 1):
        params = urlencode({'q': query + ' archived:false fork:false', 'sort': 'stars', 'per_page': 100, 'page': page})
        result = subprocess.run(['gh', 'api', 'search/repositories?' + params], capture_output=True, text=True, check=True)
        response = json.loads(result.stdout)
        for repo in response['items']:
            key = repo['full_name'].lower()
            if key in known:
                continue
            candidate = candidates.setdefault(key, {'id': repo['full_name'], 'url': repo['html_url'],
                'description': repo.get('description'), 'license': (repo.get('license') or {}).get('spdx_id'),
                'stars': repo['stargazers_count'], 'matched_queries': [], 'review_status': 'unreviewed'})
            if query not in candidate['matched_queries']:
                candidate['matched_queries'].append(query)
        if len(response['items']) < 100:
            break
out = {'generated_at': datetime.now(timezone.utc).isoformat(), 'queries': QUERIES, 'pages_per_query': args.pages,
       'note': 'Search results are unreviewed; topics can be noisy, licenses and relevance need manual verification.',
       'candidates': sorted(candidates.values(), key=lambda x: -x['stars'])}
Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
print(f"Wrote {len(candidates)} unreviewed candidates to {args.output}")
