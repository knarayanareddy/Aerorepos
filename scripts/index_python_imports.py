#!/usr/bin/env python3
"""Parse a small sample of Python files, resolving unambiguous local imports."""
import argparse, ast, base64, concurrent.futures, json, subprocess
from pathlib import Path
from urllib.parse import quote
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', help='Index one catalog repository')
parser.add_argument('--per-repo', type=int, default=5)
parser.add_argument('--workers', type=int, default=8)
args = parser.parse_args()
if args.per_repo < 1 or args.workers < 1: parser.error('limits must be positive')
files=sorted((ROOT/'data/trees').glob('*.json'))
files=[f for f in files if f.name!='failures.json' and (not args.repo or f.stem.lower()==args.repo.replace('/','__').lower())]
if args.repo and not files: parser.error('No snapshot for repository')
def run(path):
    tree=json.loads(path.read_text()); py=[p for p in tree['files'] if p.endswith('.py')][:args.per_repo]
    edges=[]; parsed=[]; failed=[]
    for source in py:
        url=f"repos/{tree['id']}/contents/{quote(source, safe='/')}?ref={tree['revision']}"
        res=subprocess.run(['gh','api',url],capture_output=True,text=True)
        if res.returncode: failed.append(source); continue
        try:
            payload=json.loads(res.stdout)
            if payload.get('encoding')!='base64' or payload.get('size',0)>500000: raise ValueError('not a small text file')
            text=base64.b64decode(payload['content']).decode('utf-8')
            parsed_ast=ast.parse(text); parsed.append(source)
        except (ValueError,UnicodeError,SyntaxError,KeyError): failed.append(source); continue
        for node in ast.walk(parsed_ast):
            if isinstance(node,ast.Import): modules=[a.name for a in node.names]; level=0
            elif isinstance(node,ast.ImportFrom): modules=[node.module] if node.module else []; level=node.level
            else: continue
            for module in modules:
                if level:
                    base=source.split('/')[:-1]
                    if level-1>len(base): continue
                    parts=base[:len(base)-(level-1)]+module.split('.')
                    candidates=['/'.join(parts)+'.py','/'.join(parts)+'/__init__.py']
                    matches=[p for p in tree['files'] if p in candidates]
                else:
                    suffix=module.replace('.','/')
                    matches=[p for p in tree['files'] if p==suffix+'.py' or p.endswith('/'+suffix+'.py') or p==suffix+'/__init__.py' or p.endswith('/'+suffix+'/__init__.py')]
                if len(matches)==1 and matches[0]!=source:
                    edges.append({'from':source,'to':matches[0],'line':node.lineno,'module':('.'*level)+module})
    tree['python_imports']={'sample_limit':args.per_repo,'parsed_files':parsed,'failed_files':failed,'edges':edges,
      'method':'Python AST; only unambiguous local matches among indexed paths. Dynamic imports, non-Python languages and files outside the sample are not analyzed.'}
    path.write_text(json.dumps(tree,ensure_ascii=False,separators=(',',':'))+'\n')
    return tree['id'],len(parsed),len(edges),len(failed)
with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
    for repo,n,e,f in pool.map(run,files): print(f'{repo}: {n} parsed, {e} links, {f} unavailable')
