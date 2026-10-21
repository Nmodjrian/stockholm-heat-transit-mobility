# Stockholm heat–transit mobility | exploratory collaboration starter

**Status: research scaffold, not empirical findings.** Designed to support discussion of three related avenues: (B) corridor-area mobility responses to heat, (C) transit connectivity and mobility resilience, and (D) conditional heat-aware *transit* demand forecasting. It is deliberately separate from the author's heat-conditioned accessibility research.

## Quick start

Python 3.10+; no third-party Python packages required for the starter.

```bash
python scripts/01_heat_events.py --input data/example/weather_demo.csv --output data/processed/heat_events_demo.csv
python scripts/02_gtfs_frequency.py --gtfs data/example/gtfs_demo.zip --date 2023-07-15 --output data/processed/gtfs_hourly_demo.csv
python scripts/03_mobility_response.py --weather data/processed/heat_events_demo.csv --mobility data/example/mobility_demo.csv --output outputs/mobility_summary_demo.csv
```

**All example data are synthetic**, including the GTFS archive. Demo outputs must not be described as Stockholm observations, evidence of heat effects, or results for a conference paper.

## Real-data workflow

1. Export permissible hourly/daily **observed air-temperature** CSV with `timestamp,temp_c` in Stockholm local time (ISO timestamps with UTC offset preferred); optionally `station_id`. Verify station metadata, quality control, daylight-saving transition, missingness, and the measurement period. SMHI historical meteorological observations: https://www.smhi.se/data/om-smhis-data/fragor-och-svar
2. Define the heat-event rules *before inspecting outcomes*. Starter uses an **illustrative absolute temperature threshold** (default 26°C) and flags hours, not epidemiologically validated heatwaves. For a paper, compare percentile-based events and minimum durations using SMHI observations; include night-temperature and UTCI analyses only when justified by available data.
3. Supply **historical** GTFS zip(s) matched to the mobility observation period, e.g. via Trafiklab KoDa https://www.trafiklab.se/api/our-apis/koda/. The example counts scheduled departures *not riders*, including frequencies expansion; trip times >24 hours and cross-midnight effects need careful review.
4. Request Marina's dataset *schema*, time coverage, geo resolution, provenance, provider approval, representativeness, and aggregated disclosure controls. Do not commit mobile-phone raw data or publish small-cell counts. The starter accepts `timestamp,zone_id,movement_count` and computes a demonstration relative percentage difference; actual analysis requires matching controls and event study.
5. Define corridor catchments **after** evaluating tower/zone support, GTFS, urban morphology and privacy. Zonal movements close to a corridor do not establish that those routes or transport modes were used.
6. Only attempt forecasting (D) with real transit ridership, validated mode labels, or suitably justified proxies; aggregate phone movements do not equal transit passenger demand.

## Folder layout

- `scripts/01_heat_events.py`: minimal heat-hour flagging on a weather CSV.
- `scripts/02_gtfs_frequency.py`: static GTFS scheduled departures by stop and local hour, respecting calendars and dated exceptions.
- `scripts/03_mobility_response.py`: synthetic-data demonstration of hourly movement contrast, not a causal estimator.
- `data/example/`: synthetic demonstration inputs.
- `data/raw/`: local real inputs; ignored by git.
- `data/processed/` and `outputs/`: generated files; ignored by git.
- `docs/research_plan.md`: collaboration questions and methodological safeguards.

## Research principles

- Distinguish *weather-station air temperature*, gridded UTCI, and microscale thermal exposure; do not treat any as interchangeable.
- Use matched normal days, day/time fixed effects, seasonality and holiday controls; check heat-event pre-trends and sensitivity to heat definitions.
- Timezone is `Europe/Stockholm`, including daylight saving; don't group ambiguous clock-hour timestamps without offsets.
- Protect provider data and publish only outputs explicitly authorized by agreements.

## External context

- CASPT 2027 call: https://www.caspt-transitdata2027.conf.kth.se/call-for-papers (scientific submissions 8 pages; deadline Nov 15, 2026)
- Trafiklab KoDa: https://www.trafiklab.se/api/our-apis/koda/
- SMHI met observations: https://opendata-download-metobs.smhi.se/api.json
