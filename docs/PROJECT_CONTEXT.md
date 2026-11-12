# ResQ Nexus — Project Context

Standing rules for every change to this repository. Read this before touching code, copy,
docs or data. If a rule here conflicts with an older comment or README line, this file wins.

## Project scope (approved project diary)

ResQ Nexus fuses satellite-based damage assessment and official alerts with citizen ground
reports into a single verified incident feed, where every incident carries a confidence score.
Satellite assessment uses a deep-learning damage model following the base paper
*DisasterReliefGPT*, trained and validated on real xBD imagery; Indian scenarios use simulated
satellite input through the same pipeline. A priority-weighted, fairness-aware Allocation Engine
plans resources across zones on real road networks, and a dispatcher sends the nearest compatible
resource (ambulances, rescue boats, shelters, medical teams, supplies) to each verified incident,
with an explanation for every decision. Also required: tracked alerts with acknowledgment and
automatic escalation, one-tap SOS, an offline rule-based first-aid guide, and a bilingual
English/Hindi interface. Demonstrated on South Indian scenarios (Aluva, Bengaluru, Visakhapatnam,
Coimbatore) and on real xBD satellite imagery, on PostgreSQL/PostGIS. Evaluation metrics:
dispatch time, allocation accuracy, alert acknowledgment rate, allocation coverage and fairness,
and damage-model accuracy.

Every change must stay aligned with this scope.

## What the project is

ResQ Nexus is an **Intelligent Disaster Response and Resource Allocation System**: a web
application that assesses damage, prioritises affected zones, allocates scarce relief through
the **Allocation Engine**, and explains each decision. Roles: citizen (SOS, nearby resources),
service provider (accept and resolve requests, manage capacity), admin (SOS monitor, approvals,
Command Centre). It is a student project and a prototype, not an operational system.

## Repository layout

| Folder | Contents |
|---|---|
| `frontend/` | React 19 + Vite client (Leaflet maps, Recharts) |
| `backend/` | FastAPI API, SQLAlchemy 2 + GeoAlchemy2 models, Alembic migrations, tests |
| `ml/` | Damage-assessment models and scripts; outputs the contracts below |
| `data/` | Scenarios (`scenarios/*.json`), demo seed, region presets — shared by backend and ml |
| `docs/` | This file, screenshots, further documentation |

Shared shapes live once, in `backend/schemas/contracts.py`: `BuildingAssessment`
(id, lat, lon, damage_class 0–3, confidence 0–1, source) and `ZoneAssessment` (zone_id,
geometry, centroid, building_count, damaged_pct, severity 0–1, population, vulnerability,
accessibility, mean_confidence, low_confidence, sos_demand, source). `source` is one of
`model` | `label` | `simulated` and is never dropped. The Allocation Engine accepts a
`Scenario` or a list of `ZoneAssessment`.

Database: PostgreSQL + PostGIS (docker-compose); locations are PostGIS `POINT` geometry
(SRID 4326) kept in sync with `latitude`/`longitude`. Schema changes go through Alembic
(`backend/alembic/versions/`). SQLite remains the fallback for tests and quick local runs.

## Design: brutalist

- **Colours:** black `#0A0A0A`, off-white `#EDEBE6`, concrete greys `#8A8A85` / `#C9C7C1`,
  signal red `#E10600`, orange `#FF6B1A` **used sparingly** (one accent per view at most).
- **Type:** heavy, tight grotesque headings (Inter Tight); Inter for body; monospace
  (IBM Plex Mono) for labels, numbers, codes and data.
- **Shape:** 1 px borders. **No** rounded corners, shadows, gradients or blur.
- **Interaction:** hard inversion on hover (background and foreground swap); no fades or
  soft states. Motion only where it carries information (counters, route drawing).
- Grids and hairlines are visible structure, not decoration.

## Documentation rule: Allocation Engine

- **"Algorithms Used"** (README, About page, reports) lists exactly three items:
  **K-Means Clustering**, **Dijkstra's Shortest Path**, **Genetic Algorithm**.
- The combined module is referred to only as the **"Allocation Engine"**.
- Do **not** name the combination or describe how the three algorithms are combined, ordered or
  feed each other — not in the README, the UI, code comments, docstrings, commit messages or
  API descriptions. Describe inputs and outputs only ("the Allocation Engine turns scores and
  stock into a plan").

## Data notice

- Every page shows the **demo-data bar** (`frontend/src/components/DemoBar.jsx`).
- Its text, and the Data Notice on About, must state **accurately** which data is real and
  which is simulated. Currently: place names and coordinates are real (OpenStreetMap); damage,
  population figures, vulnerability, accessibility, relief stock, accounts, resources and SOS
  requests are **synthetic**. Update the wording the moment real data (model output, labels,
  WorldPop counts) enters a view, and label records by their `source`.

## SOS screens

Every SOS-related screen keeps the notice, verbatim:

> **PROTOTYPE — not connected to emergency services. In a real emergency, call 112.**

(`frontend/src/components/sos/PrototypeNotice.jsx`.) It is never hidden, collapsed or
reworded.

## Base paper and datasets

- **Base paper:** *DisasterReliefGPT* — Technologies **2026**, 14, 179.
- **Datasets:**
  - **xBD** — CC BY-NC-SA 4.0; cite Gupta et al. 2019 (*xBD: A Dataset for Assessing Building
    Damage from Satellite Imagery*). Non-commercial use only.
  - **Sen1Floods11** — flood extent (Sentinel-1).
  - **OpenStreetMap** — places, boundaries, map tiles (© OpenStreetMap contributors, ODbL).
  - **WorldPop** — population.
- All four, plus the base paper, are **credited on the About page**, with licences.

## Damage assessment pipeline

- One building -> zone code path for every source: `backend/services/damage/aggregate.py`
  turns `BuildingAssessment` records (model, label or simulated) into H3 `ZoneAssessment`s.
  xBD tiles and the Indian scenarios both go through it; never aggregate elsewhere.
- Model assets (`resq_damage.onnx`, xBD samples, geotransforms, `test_results.json`) live in
  `data/assets/` (git-ignored; `backend/scripts/download_assets.py`). Without the model the app
  uses ground-truth labels and says so in the UI; without samples it says how to install them.
- The backend runs on a 512 MB server: inference must stay under 400 MB peak (tiled mode).
- All new UI text goes through react-i18next translation keys (English now, Hindi later).

## Secrets

- Secrets (`JWT_SECRET`, `GEMINI_API_KEY`, database passwords) live **only in `.env` files**
  (`.env`, `backend/.env`, `frontend/.env.local`), which are git-ignored.
- Commit only `*.env.example` files with empty values. Never paste a key into code, docs,
  compose files, CI config or a commit message.

## Engineering conventions

- Do not break existing features; `backend/tests` must pass (`python -m pytest`) and
  `npm run lint && npm run build` must succeed before a commit.
- Commit in logical steps; work on a branch and open a PR into `main`.
- Desktop-only demo; no mobile layouts are required.
- Demo accounts and their public passwords are listed in the README on purpose; they only
  exist in the synthetic seed.
