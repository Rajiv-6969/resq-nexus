# Damage assessment module — interface spec (shared by the three workstreams)

Branch base: `final` @ 333044e. Shared code already present:
`backend/services/damage/aggregate.py` (`aggregate_buildings`, `class_counts`, `severity_error`),
`backend/scripts/download_assets.py`, `backend/schemas/contracts.py` (BuildingAssessment, ZoneAssessment).
Assets in `data/assets/` (git-ignored): `resq_damage.onnx` (present), `test_results.json` (present),
`xbd_sample/` (NOT available yet — code must work with it absent and with a tiny synthetic fixture).

## Backend HTTP API (owner: backend workstream) — all under the admin role unless noted

| Method | Path | Purpose | Response |
|---|---|---|---|
| GET | `/damage/status` | model + samples availability | `{model_installed, model_path, samples_installed, sample_dir, notice, inference_mode: "full"|"tiled", low_confidence_threshold, h3_resolution}` |
| GET | `/damage/samples` | xBD tiles available | `{events: [{event, tiles: [{tile_id, has_labels, bounds:{south,west,north,east}}]}]}` |
| GET | `/damage/samples/{tile_id}/image/{pre|post}` | PNG bytes (image/png) | |
| POST | `/damage/assess` | run assessment on a sample tile or an uploaded pair | body JSON `{tile_id}` **or** multipart `pre`, `post`, `bounds` (JSON string south/west/north/east). Response = `AssessmentResult` below |
| POST | `/damage/allocate` | Allocation Engine on an assessment | body `{assessment_id}` (from a previous assess) or `{zones:[ZoneAssessment]}` plus optional `weights`, `resources` → the existing `AllocationResponse` shape (`main.py`), with `road_source` |
| GET | `/damage/metrics` | Analytics numbers | `{test_results: <test_results.json as is>, severity_error: {<event>: {zones, mae}}, severity_error_note}` (severity error computed from the sample tiles when present, cached under `data/assets/cache/`; `{}` when samples absent) |
| GET | `/admin/incidents/satellite?scenario_id=…` or `?assessment_id=…` | satellite incident candidates | `{candidates: [IncidentCandidate], threshold}` |

`AssessmentResult`:
```
{
  assessment_id: str, tile_id: str|null, event: str|null, bounds: {south,west,north,east},
  source: "model"|"label",            # label when the model is missing / failed (fallback)
  notice: str|null,                    # e.g. "Using ground-truth labels (model not installed)"
  buildings: [ {id, lat, lon, damage_class, confidence, source, polygon: [[lat,lon],...]|null} ],
  zones:     [ ZoneAssessment ],       # from aggregate_buildings (model or label buildings)
  labels:    { buildings: [...same shape...], zones: [ZoneAssessment] } | null,   # ground truth when labels exist
  counts:    { model: {0:n,1:n,2:n,3:n}, label: {...}|null },
  agreement: { matched, accuracy, per_class_f1: {0..3}, macro_f1, confusion: [[4x4]] } | null,  # model vs label, buildings matched by centroid within 5 m / IoU
  timing:    { inference_ms, peak_mb, mode: "full"|"tiled"|"none" },
  roads_cached: bool                   # a road graph exists for these bounds (Send to Allocation uses real roads)
}
```
`IncidentCandidate`:
```
{ id, type: "building-damage", disaster_type, zone_id, name, latitude, longitude, geometry, severity, damaged_pct,
  building_count, population, people_affected, source: "satellite-model"|"satellite-label"|"satellite-simulated",
  confidence, low_confidence, scenario_id|null, assessment_id|null }
```

## Scenario files (owner: scenario workstream)
- `data/scenarios/<id>.json` keeps its current shape; zones are now produced by `aggregate_buildings` from simulated
  buildings; each scenario gains `"damage": {"source": "simulated", "buildings_file": "<id>.buildings.json.gz", "building_count": N, "confidence": "scenario-defined"}`.
- `data/scenarios/<id>.buildings.json.gz`: `{"buildings": [BuildingAssessment…], "source": "simulated", "footprints": "osm"|"sampled", …}`.
- `GET /scenarios/{id}/buildings` (scenario workstream adds the route in `backend/routers/scenarios_damage.py`, included from `main.py` with one line) → `{scenario_id, source: "simulated", label: "Simulated satellite assessment", buildings: [...], counts: {0..3}}`.

## Frontend (owner: frontend workstream) consumes exactly the shapes above.
- i18n: `react-i18next` + `i18next`, `frontend/src/i18n/{index.js,en.json}`, `useTranslation()`; language toggle placeholder in the NavBar (EN active, HI disabled with tooltip "coming soon").
- Pages: `DamageAssessment.jsx` (rewrite), `admin/NewIncident.jsx` (new route `/admin/incidents/new`), Analytics gains a "Damage model" section.
- Brutalist design rules in `docs/PROJECT_CONTEXT.md` apply. Damage colours: 0 none = concrete grey `#8A8A85`, 1 minor = `#C9C7C1` outline black, 2 major = orange `#FF6B1A`, 3 destroyed = signal red `#E10600`.

## Rules for every workstream
- Read `docs/PROJECT_CONTEXT.md` first; obey the Allocation Engine documentation rule and the data notice rule.
- No network calls at app start-up or in request handlers (only in `backend/scripts/*`).
- `backend/tests` must pass: run `"C:/Users/Prasanna Stanley/resq-nexus/backend/venv/Scripts/python.exe" -m pytest -p no:warnings -q` from your worktree's `backend/` folder.
- Frontend: `node.exe "C:/Users/Prasanna Stanley/AppData/Local/hermes/tools/npm-12.0.2-win32-x64/node_modules/npm/bin/npm-cli.js" run lint` and `run build` must pass (git-bash shell; use native `C:/...` paths for node/python).
- Commit on your own branch in your own worktree; do not push; do not touch files owned by another workstream unless the spec says so.
