# Collaboration concept — questions for Marina

**B (core):** Are movement volumes, hourly profiles, and OD ties around selected Stockholm transit corridors different during local summer heat events than on comparable days?

**C (extension):** Does measured GTFS service supply/connectivity moderate these differences after appropriate land-use, calendar, weather, and socioeconomic controls?

**D (conditional):** If independent passenger counts or validated transit-mode estimates exist, do heat variables improve out-of-time forecasting of *transit passenger demand* beyond time/calendar/service/weather baselines?

## Data feasibility checklist

- [ ] Permission to process and publish derived mobile signaling measures
- [ ] Years and complete summer coverage, including heat and reference days
- [ ] Hourly/daily resolution, local versus UTC timezone and coverage artifacts
- [ ] Device counts, presence, OD, or trajectories; exact semantics
- [ ] Zonal tessellation / cell-tower catchments and spatial accuracy
- [ ] Sampling, market-share adjustments and suppression thresholds
- [ ] Any mode indicators or separate validated SL boarding data
- [ ] Candidate spatial area / corridor selection and matching GTFS snapshots
- [ ] SMHI station availability and thermal-data provenance

## Suggested staged analysis

1. Heat calendar (stockholm-specific event definitions, 1+ summers; QA).
2. Historical GTFS counts, frequency and catchment/transfer features.
3. Descriptive mobility event profiles from *permitted* aggregates.
4. Matched-event model with place/time controls and heat×transit interactions; consider nonlinearity and lag effects.
5. Forecast evaluation only if transit demand ground truth exists. Hold out **entire heat events or years**.

## Inferential guardrails

Mobile signaling near a corridor is **not** observed corridor use. GTFS trips are scheduled departures **not** observed ridership or realized service. A transit interaction in an observational model is association, not proof transit causes resilience. Avoid treating heat avoidance (fewer trips) as inherently beneficial. Include holidays, school vacation, rain, daylight, network changes and population/composition shifts.
