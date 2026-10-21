import argparse,csv,datetime as dt
from pathlib import Path

def parse_time(s):
    v=dt.datetime.fromisoformat(s)
    if v.tzinfo is None:
        raise ValueError("Timestamp must have a UTC offset (e.g., 2023-07-15T14:00:00+02:00), to disambiguate summer/winter clock times")
    return v

p=argparse.ArgumentParser(description='Illustrative hourly temperature threshold flag; not validated heatwave identification')
p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--threshold',type=float,default=26)
a=p.parse_args()
with open(a.input,newline='') as f:
    rows=list(csv.DictReader(f))
if not rows: raise ValueError('Empty input')
result=[]
for row in rows:
    t=parse_time(row['timestamp'])
    c=float(row['temp_c'])
    result.append(dict(timestamp=t.isoformat(),date=t.date().isoformat(),hour=t.hour,temp_c=c,hot_hour=int(c>=a.threshold)))
result.sort(key=lambda x:x['timestamp'])
out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
print(f'Wrote {len(result)} hourly records to {out}; {sum(int(x["hot_hour"]) for x in result)} are above {a.threshold}C (illustrative rule).')
