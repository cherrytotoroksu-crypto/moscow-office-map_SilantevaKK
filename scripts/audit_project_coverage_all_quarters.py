"""Read-only coverage audit: quarterly channels versus all_projects_layer."""
import json, re, unicodedata, os
from pathlib import Path
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=Path(os.environ.get('AUDIT_OUT',str(ROOT/'outputs')))
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def norm(v):
 s=unicodedata.normalize('NFKC',str(v or '')).lower().replace('ё','е')
 s=re.sub(r'[^0-9a-zа-я]+',' ',s,flags=re.I)
 return re.sub(r'\s+',' ',s).strip()
def names(path):
 d=load(path)
 if isinstance(d,dict) and 'projects' in d: d=d['projects']
 if isinstance(d,dict): return list(d.keys())
 if isinstance(d,list): return [x.get('name') or x.get('canonical_name') or x.get('raw_name') for x in d if isinstance(x,dict)]
 return []
def main():
 layer=load(DATA/'all_projects_layer.json'); layer_names=defaultdict(list)
 for r in layer: layer_names[norm(r.get('canonical_name') or r.get('raw_name'))].append(r.get('canonical_project_id'))
 periods=sorted({p.stem.split('_')[-1] for p in DATA.glob('*_20*.json') if p.stem.split('_')[-1].isdigit()})
 report={'generated_at':'2026-08-18','read_only':True,'periods':{},'layer_only_candidates':[]}
 seen=defaultdict(list)
 for period in periods:
  channels={}
  for channel,prefix in [('sale','lots'),('rent','rent_lots'),('flexible-office','coworking')]:
   f=DATA/f'{prefix}_{period}.json'
   if not f.exists(): channels[channel]={'file':None,'projects':[],'missing_from_layer':[]}; continue
   ns=names(f); miss=[]
   for n in ns:
    k=norm(n); seen[k].append({'period':period,'channel':channel,'name':n})
    if k and k not in layer_names: miss.append(n)
   channels[channel]={'file':f.name,'projects':len(ns),'missing_from_layer':sorted(set(miss))}
  report['periods'][period]=channels
 for k,rows in seen.items():
  if k and len({x['name'] for x in rows})>1: report.setdefault('historical_name_variants',[]).append({'normalized':k,'rows':rows})
 report['summary']={'period_count':len(periods),'layer_rows':len(layer),'missing_by_period':sum(len(v['missing_from_layer']) for p in report['periods'].values() for v in p.values())}
 OUT.mkdir(exist_ok=True); (OUT/'project_coverage_audit_all_quarters.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
 for p,c in report['periods'].items():
  m={k:len(v['missing_from_layer']) for k,v in c.items() if v['missing_from_layer']}
  if m: print(p,m)
if __name__=='__main__': main()
