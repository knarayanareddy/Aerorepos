#!/usr/bin/env python3
"""Snapshot repository trees from GitHub. No code is executed or cloned."""
import argparse
import concurrent.futures
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data/catalog.json'
OUT = ROOT / 'data/trees'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', help='Only index this owner/repo (case-insensitive)')
parser.add_argument('--workers', type=int, default=4)
parser.add_argument('--max-files', type=int, default=300, help='Maximum files per repository, default 300')
args = parser.parse_args()
if args.max_files < 1 or args.workers < 1: parser.error('limits must be positive')
projects = json.loads(CATALOG.read_text())['projects']
if args.repo:
    projects = [p for p in projects if p['id'].lower() == args.repo.lower()]
    if not projects: parser.error('repository not in catalog')
OUT.mkdir(parents=True, exist_ok=True)

def index(project):
    repo = project['id']
    commit = subprocess.run(['gh', 'api', f'repos/{repo}/commits/HEAD', '--jq', '.sha'], text=True, capture_output=True)
    if commit.returncode:
        return repo, None, commit.stderr.strip() or 'GitHub commit request failed'
    revision = commit.stdout.strip()
    response = subprocess.run(['gh', 'api', f'repos/{repo}/git/trees/{revision}?recursive=1'], text=True, capture_output=True)
    if response.returncode:
        return repo, None, response.stderr.strip() or 'GitHub request failed'
    tree = json.loads(response.stdout)
    files = [item['path'] for item in tree.get('tree', []) if item['type'] == 'blob']
    # A deterministic selection: documentation and source files before assets, then shallow paths.
    def rank(path):
        name = path.rsplit('/', 1)[-1].lower()
        ext = name.rsplit('.', 1)[-1] if '.' in name else ''
        priority = 0 if name.startswith('readme') else 1 if ext in ('py','cpp','cc','c','h','hpp','f90','f','jl','java','rs','ts','js','md') else 2
        return (priority, path.count('/'), path.lower())
    selected = sorted(files, key=rank)[:args.max_files]
    record = {'id':repo, 'revision':revision, 'tree_sha':tree['sha'], 'indexed_at':datetime.now(timezone.utc).isoformat(),
              'github_tree_truncated':tree.get('truncated', False), 'total_files_returned':len(files),
              'selection_limit':args.max_files, 'files':selected}
    return repo, record, None

failures=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
    for repo, record, error in executor.map(index, projects):
        if error:
            failures.append({'id': repo, 'error': error}); print(f'FAILED {repo}: {error}')
        else:
            name=repo.replace('/', '__')+'.json'
            (OUT/name).write_text(json.dumps(record, ensure_ascii=False, separators=(',', ':'))+'\n')
            print(f"{repo}: {len(record['files'])}/{record['total_files_returned']} files")
(OUT/'failures.json').write_text(json.dumps(failures, indent=2)+'\n')
if failures: raise SystemExit(1)
