import argparse,csv,collections,datetime as dt
from pathlib import Path
p=argparse.ArgumentParser(description='Demonstration hot versus nonhot movement means; NOT adjusted or causal')
p.add_argument('--weather',required=True);p.add_argument('--mobility',required=True);p.add_argument('--output',required=True)
a=p.parse_args()
with open(a.weather,newline='') as f:weather={r['timestamp']:int(r['hot_hour']) for r in csv.DictReader(f)}
with open(a.mobility,newline='') as f:mobility=list(csv.DictReader(f))
groups=collections.defaultdict(list)
for r in mobility:
    flag=weather.get(r['timestamp'])
    if flag is None:continue
    hour=dt.datetime.fromisoformat(r['timestamp']).hour
    groups[(r['zone_id'],hour,flag)].append(float(r['movement_count']))
outrows=[]
keys=sorted({(zone,hour) for zone,hour,flag in groups})
for zone,hour in keys:
    cool=groups.get((zone,hour,0),[]);hot=groups.get((zone,hour,1),[])
    if not cool or not hot:continue
    c=sum(cool)/len(cool);h=sum(hot)/len(hot)
    outrows.append(dict(zone_id=zone,hour=hour,n_reference=len(cool),n_hot=len(hot),mean_reference=round(c,2),mean_hot=round(h,2),relative_change_pct=round((h/c-1)*100,2) if c else ''))
out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['zone_id','hour','n_reference','n_hot','mean_reference','mean_hot','relative_change_pct']);w.writeheader();w.writerows(outrows)
print(f'Wrote {len(outrows)} illustrative comparisons to {out}; NOT event-matched, and NOT causal.')
