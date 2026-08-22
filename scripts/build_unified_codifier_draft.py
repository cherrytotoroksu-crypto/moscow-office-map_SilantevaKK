"""Build a deterministic, non-destructive unified codifier draft.

The draft keeps existing canonical IDs as legacy references and does not
rewrite any source file. Exact normalized name matching is intentionally
conservative; unresolved names go to review_queue.
"""
from __future__ import annotations
import json, re, unicodedata, os
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=Path(os.environ.get('AUDIT_OUT',str(ROOT/'outputs')))
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def norm(v):
 s=unicodedata.normalize('NFKC',str(v or '')).lower().replace('ё','е')
 s=re.sub(r'[^0-9a-zа-я]+',' ',s,flags=re.I)
 return re.sub(r'\s+',' ',s).strip()
def top_names(p):
 d=load(p)
 if isinstance(d,dict) and 'projects' in d: d=d['projects']
 if isinstance(d,dict): return list(d)
 return [x.get('name') or x.get('canonical_name') or x.get('raw_name') for x in d if isinstance(x,dict)]
def main():
 layer=load(DATA/'all_projects_layer.json')
 # Stable draft order: existing canonical IDs first, never dependent on file order.
 layer=sorted(layer,key=lambda r:(str(r.get('canonical_project_id') or ''),str(r.get('canonical_building_id') or '')))
 by_name=defaultdict(list)
 for r in layer:
  for v in [r.get('canonical_name'),r.get('raw_name'),*(r.get('aliases') or [])]:
   if norm(v): by_name[norm(v)].append(r.get('canonical_project_id'))
 projects=[]
 for i,r in enumerate(layer,1):
  pid=r.get('canonical_project_id')
  projects.append({'project_id':f'PRJ-{i:04d}','legacy_ids':[pid] if pid else [],'canonical_project_id':pid,'canonical_name':r.get('canonical_name'),'aliases':r.get('aliases') or [],'developer':r.get('developer'),'address':r.get('address'),'latitude':r.get('latitude'),'longitude':r.get('longitude'),'gla':r.get('gla'),'gba':r.get('gba'),'entity_grain':r.get('entity_grain'),'source':r.get('source'),'verification_status':r.get('verification_status'),'confidence':r.get('confidence'),'quarter_refs':[]})
 unresolved=[]
 for p in sorted(DATA.glob('*_20*.json')):
  if p.name=='building_dates.json' or p.name.startswith('future_projects'): continue
  channel='sale' if p.name.startswith('lots_') else 'rent' if p.name.startswith('rent_lots_') else 'flexible-office' if p.name.startswith('coworking_') else 'building'
  period=p.stem.split('_')[-1]
  for name in top_names(p):
   k=norm(name); ids=sorted(set(by_name.get(k,[])))
   if len(ids)==1:
    for row in projects:
     if row['canonical_project_id']==ids[0]: row['quarter_refs'].append({'period':period,'channel':channel,'source':p.name,'raw_name':name})
   elif k and channel in {'sale','rent'} and name not in {'A','A+','B','B+'}:
    unresolved.append({'period':period,'channel':channel,'raw_name':name,'source':p.name,'reason':'no unique exact canonical match'})
 # Deduplicate refs and preserve a review queue instead of guessing.
 for row in projects:
  row['quarter_refs']=sorted({json.dumps(x,ensure_ascii=False,sort_keys=True):json.dumps(x,ensure_ascii=False,sort_keys=True) for x in row['quarter_refs']})
  row['quarter_refs']=[json.loads(x) for x in row['quarter_refs']]
 draft={'schema_version':'0.1-draft','generated_at':'2026-08-18','read_only_sources':True,'id_policy':'PRJ draft only; do not replace legacy IDs','project_count':len(projects),'projects':projects,'review_queue':unresolved}
 OUT.mkdir(exist_ok=True); (OUT/'unified_codifier_draft.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'project_count':len(projects),'review_queue':len(unresolved)},ensure_ascii=False))
if __name__=='__main__': main()
