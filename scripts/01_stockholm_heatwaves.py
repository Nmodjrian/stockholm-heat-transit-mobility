#!/usr/bin/env python3
"""Download SMHI hourly air temperature and identify Stockholm summer heat episodes.

Example: python scripts/01_stockholm_heatwaves.py --years 2019 2020 2021 2022 2023
Dependencies: pandas matplotlib requests
"""
import argparse
import json
import csv
import io
import logging
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import requests

BASE = 'https://opendata-download-metobs.smhi.se/api/version/latest/parameter/1'
STOCKHOLM = (59.3293, 18.0686)
LOG = logging.getLogger('stockholm_heatwaves')


def get_json(url):
    response = requests.get(url, timeout=90, headers={'User-Agent':'stockholm-heat-transit-mobility-research/0.1'})
    response.raise_for_status()
    return response.json()


def discover_stations(radius_deg=0.5):
    """Discover candidate stations using SMHI parameter metadata; no hardcoded station IDs."""
    data = get_json(BASE + '.json')
    stations = data.get('station', data.get('stations', []))
    candidates = []
    for s in stations:
        try:
            lat = float(s.get('latitude'))
            lon = float(s.get('longitude'))
            distance = ((lat - STOCKHOLM[0])**2 + ((lon-STOCKHOLM[1])*0.54)**2)**0.5
            if distance <= radius_deg:
                candidates.append((distance, s))
        except (TypeError, ValueError):
            continue
    return [s for _,s in sorted(candidates, key=lambda x:x[0])]


def fetch_station(station_id, period):
    extension = 'csv' if period == 'corrected-archive' else 'json'
    url = f'{BASE}/station/{station_id}/period/{period}/data.{extension}'
    response = requests.get(url, timeout=120, headers={'User-Agent':'stockholm-heat-transit-mobility-research/0.2'})
    response.raise_for_status()
    if extension == 'csv':
        return parse_archive_csv(response.content.decode('utf-8-sig', errors='replace'))
    return parse_values(response.json())


def parse_archive_csv(text):
    """Read SMHI corrected-archive CSV with Swedish preamble and semicolon delimiter."""
    lines = text.splitlines()
    header_i = next((i for i, line in enumerate(lines)
                     if line.startswith('Datum;') and 'Tid (UTC)' in line), None)
    if header_i is None:
        raise ValueError('SMHI archive CSV has no recognized Datum;Tid (UTC) header')
    reader = csv.DictReader(io.StringIO('\n'.join(lines[header_i:])), delimiter=';')
    records = []
    for row in reader:
        try:
            date = row.get('Datum', '').strip()
            time = row.get('Tid (UTC)', '').strip()
            if not date or not time:
                continue
            temperature_text = row.get('Lufttemperatur')
            if temperature_text is None:
                # Fall back to third column, since SMHI may change the measurement label.
                keys = reader.fieldnames or []
                if len(keys) < 3:
                    continue
                temperature_text = row.get(keys[2], '')
            temperature = float(temperature_text.replace(',', '.').strip())
            stamp = pd.to_datetime(f'{date} {time}', utc=True, errors='coerce')
            if pd.isna(stamp):
                continue
            records.append({'timestamp_utc': stamp,
                            'temperature_c': temperature,
                            'quality': row.get('Kvalitet', '')})
        except (TypeError, ValueError):
            continue
    return pd.DataFrame(records, columns=['timestamp_utc','temperature_c','quality'])


def parse_values(payload):
    values = payload.get('value', payload.get('values', []))
    records = []
    for v in values:
        try:
            records.append({'timestamp_utc':pd.to_datetime(int(v['date']), unit='ms', utc=True),
                            'temperature_c':float(str(v['value']).replace(',','.')),
                            'quality':v.get('quality','')})
        except (KeyError, TypeError, ValueError):
            continue
    if not records:
        return pd.DataFrame(columns=['timestamp_utc','temperature_c','quality'])
    return pd.DataFrame(records).drop_duplicates('timestamp_utc',keep='last').sort_values('timestamp_utc')


def acquire(years, station_id=None):
    candidates = ([{'key':str(station_id),'name':f'Manual station {station_id}'}] if station_id else discover_stations())
    if not candidates:
        raise RuntimeError('No Stockholm stations found in SMHI metadata. Try --station-id with a verified station ID.')
    best = None
    for station in candidates[:15]:
        sid = station.get('key')
        try:
            archive = fetch_station(sid,'corrected-archive')
            try:
                recent = fetch_station(sid,'latest-months')
            except requests.RequestException:
                recent = pd.DataFrame(columns=['timestamp_utc','temperature_c','quality'])
            combined = pd.concat([archive,recent],ignore_index=True)
            if combined.empty: continue
            combined = combined.drop_duplicates('timestamp_utc',keep='last').sort_values('timestamp_utc')
            filtered = combined[combined.timestamp_utc.dt.year.isin(years)].copy()
            filtered = filtered[filtered.timestamp_utc.dt.month.isin([6,7,8])]
            if filtered.empty: continue
            # Prefer a station providing at least 85% of requested summer hours.
            expected = len(years)*92*24
            coverage = len(filtered)/expected
            LOG.info('Candidate %s (%s): %.1f%% hourly coverage',sid,station.get('name'),coverage*100)
            filtered['station_id'] = sid
            filtered['station_name'] = station.get('name','')
            if best is None or coverage > best[2]:
                best = (filtered, station, coverage)
            if coverage >= .85:
                return filtered, station, coverage
        except (requests.RequestException, ValueError) as e:
            LOG.warning('Station %s: %s',sid,e)
            continue
    if best is not None:
        LOG.warning('Best station covers only %.1f%% of requested summer hours; incomplete years need review.', best[2]*100)
        return best
    raise RuntimeError('No usable station found. Try a verified --station-id or check SMHI API connectivity.')


def analyze(df, threshold=25.0, min_days=3, min_valid_hours=18):
    """Screening heatwave definition: >=threshold daily maximum for >=min_days consecutive days.
    This is a selectable research definition, NOT a verified Swedish official heat-warning threshold.
    Days with sparse hourly coverage remain unclassified, not cool.
    """
    hourly = df.copy()
    hourly['time_local'] = hourly.timestamp_utc.dt.tz_convert('Europe/Stockholm')
    hourly['local_date'] = hourly.time_local.dt.date
    hourly['local_hour'] = hourly.time_local.dt.hour
    hourly['hot_hour'] = hourly.temperature_c >= threshold
    daily = hourly.groupby('local_date').agg(
        tmax_c=('temperature_c','max'), tmin_c=('temperature_c','min'),
        tmean_c=('temperature_c','mean'), observed_hours=('temperature_c','count'),
        hot_hours=('hot_hour','sum')).reset_index()
    daily['local_date'] = pd.to_datetime(daily.local_date)
    daily['eligible'] = daily.observed_hours >= min_valid_hours
    daily['hot_day'] = daily.eligible & (daily.tmax_c>=threshold)
    daily['event_id'] = pd.NA
    events=[]
    next_id=1
    # Evaluate continuous calendar sequence, breaking at gaps and year transitions.
    full_dates = pd.date_range(daily.local_date.min(),daily.local_date.max(),freq='D')
    daily = daily.set_index('local_date').reindex(full_dates).rename_axis('local_date').reset_index()
    daily['hot_day'] = daily.hot_day.fillna(False).astype(bool)
    daily['event_id'] = pd.Series([pd.NA]*len(daily),dtype='Int64')
    run=[]
    def close_run(run):
        nonlocal next_id
        if len(run)>=min_days:
            run_rows=daily.loc[run]
            daily.loc[run,'event_id']=next_id
            events.append({'event_id':next_id,'start_date':str(run_rows.local_date.iloc[0].date()),
                           'end_date':str(run_rows.local_date.iloc[-1].date()),'duration_days':len(run),
                           'peak_tmax_c':float(run_rows.tmax_c.max()),'mean_tmax_c':float(run_rows.tmax_c.mean())})
            next_id+=1
    for i,hot in enumerate(daily.hot_day):
        if hot: run.append(i)
        else:
            close_run(run);run=[]
    close_run(run)
    daily['year']=daily.local_date.dt.year
    event_lookup=daily.set_index(daily.local_date.dt.date)['event_id']
    hourly['event_id']=hourly['local_date'].map(event_lookup)
    return hourly,daily,pd.DataFrame(events,columns=['event_id','start_date','end_date','duration_days','peak_tmax_c','mean_tmax_c'])


def run(years, output_dir, station_id=None, threshold=25.0,min_days=3,min_valid_hours=18, input_csv=None):
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    if input_csv:
        df=pd.read_csv(input_csv)
        df['timestamp_utc']=pd.to_datetime(df['timestamp_utc'],utc=True)
        df=df[df.timestamp_utc.dt.year.isin(years) & df.timestamp_utc.dt.month.isin([6,7,8])]
        station={'key':'local-file','name':'User provided hourly temperature observations'}
        coverage=None
    else:
        df,station,coverage=acquire(years,station_id)
    if df.empty:
        raise RuntimeError('No summer observations for the years requested.')
    hourly,daily,events=analyze(df,threshold,min_days,min_valid_hours)
    hourly.to_csv(output_dir/'stockholm_hourly_temperature.csv',index=False)
    daily.to_csv(output_dir/'stockholm_daily_heat_flags.csv',index=False)
    events.to_csv(output_dir/'stockholm_heat_events.csv',index=False)
    fig,ax=plt.subplots(figsize=(12,4))
    ax.plot(daily.local_date,daily.tmax_c,lw=0.85,label='Daily maximum temperature')
    ax.axhline(threshold,linestyle='--',label=f'Screening threshold {threshold:g} °C')
    for _,e in events.iterrows():
        ax.axvspan(pd.Timestamp(e.start_date),pd.Timestamp(e.end_date)+pd.Timedelta(days=1),alpha=.14)
    ax.set(title='Stockholm summer heat screening (SMHI station observations)',ylabel='Daily maximum air temperature (°C)',xlabel='Local date')
    ax.legend(loc='best');fig.tight_layout()
    fig.savefig(output_dir/'stockholm_heat_events.png',dpi=160)
    plt.close(fig)
    meta={'source':'SMHI MetObs hourly air temperature (parameter 1)' if not input_csv else str(input_csv),
          'station_id':station.get('key'),'station_name':station.get('name'),
          'station_coverage_estimate':coverage,'years':years,'threshold_c':threshold,
          'min_consecutive_days':min_days,'min_daily_observed_hours':min_valid_hours,
          'method_note':'Exploratory threshold-based events; station air temperature, NOT corridor-level UTCI.',
          'timezone':'Europe/Stockholm (observations delivered in UTC)'}
    (output_dir/'analysis_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    LOG.info('Wrote %s; %d event(s) identified',output_dir,len(events))
    return hourly,daily,events


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--years',type=int,nargs='+',default=[2019,2020,2021,2022,2023])
    p.add_argument('--output-dir',default='data/processed/stockholm_heat')
    p.add_argument('--station-id',help='Optional SMHI station ID. Otherwise auto-discover near Stockholm.')
    p.add_argument('--threshold',type=float,default=25.0)
    p.add_argument('--min-days',type=int,default=3)
    p.add_argument('--min-valid-hours',type=int,default=18)
    p.add_argument('--input-csv',help='Optional offline file with timestamp_utc and temperature_c columns')
    args=p.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s: %(message)s')
    run(args.years,args.output_dir,args.station_id,args.threshold,args.min_days,args.min_valid_hours,args.input_csv)

if __name__=='__main__': main()
