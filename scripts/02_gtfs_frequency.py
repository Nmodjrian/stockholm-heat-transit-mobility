import argparse,csv,datetime as dt,zipfile,collections
from pathlib import Path

def rows(z,name,optional=False):
    if name not in z.namelist():
        if optional:return []
        raise FileNotFoundError(f'{name} not found in GTFS')
    with z.open(name) as f:
        import io
        return list(csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig')))

def seconds(s):
    hh,mm,ss=map(int,s.split(':'));return hh*3600+mm*60+ss

def active_service_ids(z,date):
    d=date.strftime('%Y%m%d'); weekday=date.strftime('%A').lower(); ids=set()
    for r in rows(z,'calendar.txt',True):
        if r['start_date']<=d<=r['end_date'] and r[weekday]=='1':ids.add(r['service_id'])
    for r in rows(z,'calendar_dates.txt',True):
        if r['date'] == d:
            if r['exception_type']=='1':ids.add(r['service_id'])
            elif r['exception_type']=='2':ids.discard(r['service_id'])
    if 'calendar.txt' not in z.namelist() and 'calendar_dates.txt' not in z.namelist():
        raise ValueError('Need calendar or calendar_dates in GTFS')
    return ids

p=argparse.ArgumentParser(description='Scheduled GTFS stop departures by local GTFS hour, not ridership')
p.add_argument('--gtfs',required=True);p.add_argument('--date',required=True,help='YYYY-MM-DD');p.add_argument('--output',required=True)
a=p.parse_args();day=dt.date.fromisoformat(a.date)
with zipfile.ZipFile(a.gtfs) as z:
    services=active_service_ids(z,day)
    trips={r['trip_id']:r for r in rows(z,'trips.txt') if r['service_id'] in services}
    # Basic GTFS frequency expansion for exact_times=1 only; omit uncertain headway service and warn.
    freqs=collections.defaultdict(list)
    for r in rows(z,'frequencies.txt',True):freqs[r['trip_id']].append(r)
    base_times=collections.defaultdict(list)
    for r in rows(z,'stop_times.txt'):
        if r['trip_id'] in trips and r.get('departure_time'):
            base_times[r['trip_id']].append(r)
    counts=collections.Counter();omitted=0
    for tid,stops in base_times.items():
        if tid in freqs:
            stops.sort(key=lambda r:int(r['stop_sequence']))
            first=seconds(stops[0]['departure_time'])
            for fr in freqs[tid]:
                if fr.get('exact_times','0') != '1': omitted+=1;continue
                for start in range(seconds(fr['start_time']),seconds(fr['end_time']),int(fr['headway_secs'])):
                    for s in stops:
                        if s.get('pickup_type','0') == '1':continue
                        when=start+(seconds(s['departure_time'])-first)
                        counts[(s['stop_id'],when//3600)] += 1
        else:
            for s in stops:
                if s.get('pickup_type','0') == '1':continue
                counts[(s['stop_id'],seconds(s['departure_time'])//3600)] += 1
out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['date','stop_id','gtfs_service_hour','scheduled_departures'])
    for (stop,hour),count in sorted(counts.items()):w.writerow([day.isoformat(),stop,hour,count])
print(f'Wrote {len(counts)} stop-hour combinations to {out}. {omitted} frequency entries with exact_times!=1 omitted. Hours >=24 reflect next calendar day.')
