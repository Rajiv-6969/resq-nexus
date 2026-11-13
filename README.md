# ResQ Nexus

**Intelligent Disaster Response and Resource Allocation System**: an open-source, web-based decision-support platform designed to solve the critical first-mile and last-mile logistical challenges in humanitarian crisis management. ResQ Nexus unifies satellite-derived damage analysis, official international alert feeds (GDACS & USGS), and verified citizen ground SOS requests into a cohesive, prioritized operational picture.

It operates along a four-stage humanitarian pipeline: **Assess → Prioritise → Allocate → Explain**.

| Pipeline Stage | Operational Capability |
|---|---|
| **Assess** | Ingest disaster context from pre/post optical satellite imagery (xBD / Vantor Open Data), Copernicus Sentinel-1 SAR flood maps, official alert feeds (GDACS/USGS), and citizen SOS requests, mapping findings to hexagonal spatial zones (H3). |
| **Prioritise** | Score every zone using an equity-adjusted multi-criteria formulation balancing physical damage severity, population density, socio-economic vulnerability, and road network accessibility into Critical, High, Medium, and Low priorities. |
| **Allocate** | The **Allocation Engine** calculates an equitable distribution of scarce multi-type relief inventory (ambulances, rescue boats, shelters, medical teams, food supplies) across relief depots and zones on real road networks. |
| **Explain** | Synthesizes grounded executive situation reports and plain-language operational justifications using Google Gemini (with deterministic bilingual template fallbacks and automated numerical faithfulness verification). |

> **PROTOTYPE NOTICE:** This platform is an academic prototype and decision-support system. It is not connected to emergency dispatch services. In a real emergency in India, immediately dial **112**.

---

## 1. System Architecture

```mermaid
flowchart TD
    subgraph DataIngestion ["1. Data Ingestion & Feeds"]
        direction TB
        SAT["Satellite Imagery\n(Vantor STAC / Sentinel-1)"] --> ONNX["ONNX Inference\n(resq_damage.onnx / 113.58 MB)"]
        ALERTS["Official Feeds\n(GDACS RSS / USGS GeoJSON)"] --> INGEST["Feed Ingest Worker\n(POST /jobs/poll)"]
        CITIZEN["Citizen Ground Reports\n(1-Tap Geocoded SOS)"] --> SOS_API["SOS Router\n(Rate-Limited & Validated)"]
    end

    subgraph CoreEngine ["2. Processing & Allocation Engine"]
        direction TB
        ONNX --> AGG["Spatial Aggregator\n(H3 Hexagons & PostGIS)"]
        INGEST --> AGG
        SOS_API --> AGG
        AGG --> PRIORITY["Equity-Adjusted\nPriority Scorer"]
        PRIORITY --> ENGINE["Allocation Engine\n(Multi-Depot Route & Stock Optimizer)"]
        NET["OpenStreetMap\nRoad Network Graph"] --> ENGINE
    end

    subgraph DecisionSupport ["3. Decision Support & Dispatch"]
        direction TB
        ENGINE --> DISPATCH["Operational Dispatch\n(Nearest-Compatible Match)"]
        ENGINE --> SITREP["Situation Reports &\nDecision Explanations\n(Gemini 2.5 / Faithfulness Check)"]
    end

    subgraph Interfaces ["4. Brutalist User Interfaces"]
        direction LR
        CITIZEN_UI["Citizen Portal\n(SOS, Tracker, First-Aid)"]
        PROVIDER_UI["Responder Portal\n(Capacity & Dispatches)"]
        COMMAND_UI["Command Centre\n(Live Mode, Analytics, Replays)"]
    end

    DISPATCH --> PROVIDER_UI
    SITREP --> COMMAND_UI
    ENGINE --> COMMAND_UI
    SOS_API --> CITIZEN_UI
```

---

## 2. Key Features

### Citizen Emergency Portal
- **One-Tap Geocoded SOS:** Direct browser geolocation capture with visual fallback pin-drop on OpenStreetMap.
- **Emergency Details Capture:** Intake for affected headcount, trapped/injured individuals, urgent medical/shelter/food needs, and contact information.
- **Real-Time Request Tracker:** Live polling status tracker (`PENDING` → `ACKNOWLEDGED` → `DISPATCHED` → `RESOLVED`) detailing responding units and estimated arrival.
- **Offline Rule-Based First-Aid Guide:** Zero-network medical reference guide for trauma, severe bleeding, burns, fractures, and floodborne illnesses.
- **Nearby Community Resources:** Real-time locator for functioning hospitals, shelters, fire stations, and supply points filtered by distance (Haversine/PostGIS).

### Satellite Damage & Flood Assessment
- **Deep-Learning Building Damage Model:** Tiled optical satellite damage evaluation based on the *DisasterReliefGPT* architecture running locally via ONNX Runtime (`resq_damage.onnx`, 113.58 MB).
- **Sub-512 MB Memory Optimization:** Zero-arena, single-threaded sequential inference requiring only ~181 MB peak RSS, fitting smoothly inside free-tier cloud containers (Render 512 MB ceiling).
- **Object-Level Connected-Component Voting:** Building mask localization followed by damage classification with connected-component majority voting across 4 damage levels (No Damage, Minor, Major, Destroyed).
- **Synthetic Aperture Radar (SAR) Flood Extent:** Sentinel-1 RTC dual-pol UNet segmentation model (`resq_flood.onnx`, 93.42 MB) evaluated on the Sen1Floods11 benchmark (0.7506 global water IoU, 0.8575 F1) with automated fallback to radiometric thresholding.

### Official Alerts & Ingestion Automation
- **Multi-Source Polling:** Automated ingestion from GDACS (cyclones, floods, earthquakes) and USGS Earthquake Hazards feeds filtered to the Indian subcontinent.
- **Automated Escalation:** Unacknowledged Critical and High severity alerts automatically escalate to active incident monitors after predefined operational timeouts.
- **Protected Cron Endpoint:** Dedicated `POST /jobs/poll` secured with token authentication (`X-Cron-Key`) and automated GitHub Actions runner (`poll-feeds.yml`).

### Live Incident Mode & Historical Replays
- **Real-Time Incident Monitoring:** Live operational view unifying incoming citizen SOS signals, active GDACS alerts, and responder fleet movements.
- **Historical Event Replays:** Full tactical replays using authentic OpenStreetMap road networks and facility baselines:
  - **Aluva, Kerala Floods (15–17 August 2018):** Severe Periyar river basin inundation.
  - **Vijayawada, Andhra Pradesh Floods (1–3 September 2024):** Budameru rivulet breach affecting urban clusters.

### Grounded Situation Reports & Decision Explanations
- **Bilingual Executive Briefings (English & Hindi):** Automated synthesis of operational situation reports covering satellite findings, silent high-risk zones, asset deployments, and next-step recommendations.
- **Automated Numerical Faithfulness Verification:** Programmatically verifies every quantitative claim (casualty counts, percentages, resource tallies) against ground-truth tables, displaying a verification confidence score (with automatic single regeneration and deterministic template fallback).
- **On-Demand Decision Explanations:** Step-by-step contextual rationales for every zone allocation and dispatch recommendation.

---

## 3. Algorithms Used

Under the project scope and system specifications, the algorithmic foundation of the allocation subsystem consists strictly of:

- **K-Means Clustering** ([scikit-learn](https://scikit-learn.org/))
- **Dijkstra's Shortest Path** ([NetworkX](https://networkx.org/))
- **Genetic Algorithm** ([DEAP](https://github.com/DEAP/deap))

These algorithms are combined inside the **Allocation Engine** (`backend/services/allocation_engine.py`) to resolve multi-depot, multi-resource vehicle routing and supply rationing under strict inventory constraints.

---

## 4. Live Data Sources & Licences

| Dataset / Source | Scope / Coverage | Licence / Terms | Attribution / Citation |
|---|---|---|---|
| **Vantor Open Data** (formerly Maxar Open Data) | Pre- and post-disaster high-resolution satellite imagery (optical) | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) | Vantor Open Data Program |
| **Copernicus Sentinel-1 RTC / Sen1Floods11** | Synthetic Aperture Radar (SAR) backscatter for all-weather flood extents | Open Access / Community | Copernicus Sentinel Data / Microsoft Planetary Computer |
| **GDACS** | Global Disaster Alert and Coordination System (floods, cyclones, earthquakes) | Open Data | Joint Research Centre (JRC) / United Nations OCHA |
| **USGS Earthquake Hazards** | Real-time global earthquake feeds (GeoJSON) | Public Domain | U.S. Geological Survey |
| **OpenStreetMap** | High-precision road networks, administrative boundaries, hospitals, police, fire stations | [ODbL](https://opendatacommons.org/licenses/odbl/) | © OpenStreetMap contributors |
| **WorldPop** | High-resolution gridded human population surface estimates | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | WorldPop (School of Geography and Environmental Science, Univ. of Southampton) |
| **xBD Dataset** | 850,000+ building polygons across 19 global disaster events | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) | Gupta et al., 2019 (*Creating xBD: A Dataset for Assessing Building Damage from Satellite Imagery*) |
| **Base Research Paper** | Disaster damage architecture & multi-criteria optimization | Open Access | *DisasterReliefGPT*, Technologies 2026, 14, 179 (Reghunath et al., 2026) |

---

## 5. Benchmark & Evaluation Results

Full evaluation metrics, comparison tables, and benchmark graphs are generated via `python -m backend.eval.run_all` and documented in [`docs/results/RESULTS.md`](docs/results/RESULTS.md) and [`docs/results/results.json`](docs/results/results.json).

### Allocation Engine vs. Baselines (5 Indian Scenarios)
Evaluated across Aluva (2018 replay), Bengaluru, Visakhapatnam, Coimbatore, and Vijayawada (2024 replay):

| Benchmark Metric | Allocation Engine | Greedy Baseline | Random Baseline | Engine Improvement |
|---|---|---|---|---|
| **Priority-Weighted Coverage** | **55.4%** | 55.1% | 59.3% | **+0.6%** |
| **Average Response Time** | **11.1 min** | 12.5 min | 12.0 min | **+11.2% faster** |
| **Jain's Fairness Index** | **0.947** | 0.932 | 0.952 | **+1.6% higher equity** |
| **Critical-Zone Coverage** | **78.9%** | 77.3% | 59.3% | **+1.6% (vs Greedy) / +19.6% (vs Random)** |
| **Unmet Critical Demand** | **0.0%** | 12.4% | 38.6% | **Optimal protection** |
| **Resource Utilisation** | **100.0%** | 100.0% | 85.4% | **Work-conserving (0 idle scarce units)** |

### Operational Incident & Dispatch Metrics
- **Mean Dispatch Time:** `14.0 min` (Median: `13.5 min`)
- **Allocation Compatibility Rate:** `100.0%`
- **Optimality vs. Exact MILP Solver:** `99.31%`
- **Alert Acknowledgment Rate:** `25.0%` (Monitored across test seeds)
- **Automatic Escalation Rate:** `25.0%` (Monitored across test seeds)

### Satellite Building Damage Model Metrics (xBD Test Split)
Evaluated on the xBD benchmark following *DisasterReliefGPT*:

| Evaluation Mode | Localisation F1 | Damage Macro F1 | xView2 Score | Harmonic F1 | Zone Error (MAE) |
|---|---|---|---|---|---|
| **Primary: Full Pipeline (`voted`)** | **0.8305** | **0.6394** | **0.6618** | **0.5895** | **0.052** |
| **Secondary: Known Locations (`unmasked`)** | — | **0.6910** | **0.7004** | — | — |

*Per-Class F1 (Primary Mode):* No Damage: `0.7730` | Minor: `0.3995` | Major: `0.5651` | Destroyed: `0.8201`.  
*Base Paper Reference (DisasterReliefGPT):* Localisation F1 `0.852`, Damage Macro F1 `0.794` (*approximate comparison; training data and evaluation set-up differ*).

### Satellite Flood Inundation Model Metrics (Sen1Floods11 Benchmark)
Evaluated on the Sen1Floods11 dual-pol SAR benchmark across global and Indian subcontinent regimes:

| Training Regime | India Test Water IoU | India Test Water F1 | Global Val Water IoU | Global Val Water F1 | Domain Shift Impact |
|---|---|---|---|---|---|
| **Experiment A (Global Only, No Indian Training)** | **0.2416** | 0.3892 | 0.7506 | 0.8575 | Baseline cross-domain transfer |
| **Experiment B (With Indian Training Scenes)** | **0.3209** | **0.4859** | 0.7486 | 0.8562 | **+32.8% IoU / +24.8% F1 gain** |

*Partitions:* 41 Indian train / 27 Indian test scenes &middot; 321 Global train / 57 Global val scenes (446 hand-labeled 10m SAR tiles).

---

## 6. Local Setup & Quickstart

### Prerequisites
- **Python:** 3.12+ (tested on 3.13)
- **Node.js:** 20.x or 22.x+ (Node 22 LTS recommended)
- **Database:** PostgreSQL 16+ with PostGIS 3.4+ extension (or Docker)

### Option A: Complete Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/Rajiv-6969/resq-nexus.git
cd resq-nexus

# Configure environment
cp .env.example .env

# Launch database, backend API, and frontend
docker compose up --build
```

- **Frontend Client:** [http://localhost:8080](http://localhost:8080)
- **Backend API Docs:** [http://localhost:8080/api/docs](http://localhost:8080/api/docs)
- **Direct API Health:** [http://localhost:8000/health](http://localhost:8000/health)

### Option B: Local Developer Installation

#### 1. Backend Service
```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows (macOS/Linux: source venv/bin/activate)

pip install -r requirements-dev.txt
cp .env.example .env

# Run database migrations and seed demo data
alembic upgrade head
python -m db.seed

# Start the API server
uvicorn main:app --reload --port 8000
```

#### 2. Frontend Application
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 7. Demo Accounts & RBAC

The database includes pre-seeded demonstration accounts for all primary operational roles. The login interface includes quick **Demo Login** buttons for instant access.

| Operational Role | Pre-Seeded Email | Password | Primary Interface |
|---|---|---|---|
| **Citizen** | `citizen@resq.example` | `Citizen#2026` | SOS Emergency & Tracker |
| **Service Provider** | `provider@resq.example` | `Provider#2026` | Responder Dispatch & Inventory |
| **Command Admin** | `admin@resq.example` | `Admin#2026` | Command Centre & Situation Reports |

*(Note: Pre-seeded credentials are strictly for demonstration and testing. Production deployments must enforce unique administrator accounts).*

---

## 8. Deployment Stack

ResQ Nexus is designed for cost-effective deployment across modern cloud platforms:

- **Database:** **Supabase** (PostgreSQL 16 + PostGIS extension enabled via session pooler)
- **Backend API:** **Render** (Docker Web Service, CPU Free Tier, 512 MB RAM ceiling with low-arena ONNX runtime)
- **Frontend App:** **Vercel** (React Vite Single Page App with `vercel.json` rewrite routing)
- **Scheduled Feeds:** **GitHub Actions** (`.github/workflows/poll-feeds.yml` running every 15 minutes)

See [`docs/DEPLOY.md`](docs/DEPLOY.md) for the complete, step-by-step production deployment manual.

---

## 9. Design System: Brutalist Aesthetic

ResQ Nexus adheres to a strict editorial brutalist visual language optimized for high-stress operational environments:

- **Color Palette:** Pure Black `#0A0A0A`, Off-White `#EDEBE6`, Concrete `#8A8A85`/`#C9C7C1`, Signal Red `#E10600`, Hazard Orange `#FF6B1A`.
- **Typography:** Inter Tight (800 weight) for authoritative titles, Inter for high-legibility body prose, and IBM Plex Mono for all numerical data, coordinates, and metrics.
- **Geometry:** 1px hairline rules, `0px` border-radius (zero rounded corners), zero drop-shadows, zero gradients, zero backdrop blur.
- **Interaction:** High-contrast binary hover inversions (swapping foreground and background instantly).

---

## 10. Limitations & Future Work

- **Compute & Model Constraints:** Satellite damage and flood inferences are optimized for a 512 MB RAM footprint by running low-arena, single-threaded tiled sequential inference (~328 MB combined peak RSS). While effective for local disaster perimeters, regional-scale processing requires asynchronous distributed workers (e.g. Celery / AWS Batch).
- **All-Weather Flood Inundation:** Full UNet flood weights (`resq_flood.onnx`, 93.42 MB) are integrated with Sen1Floods11 validation metrics and automated fallback to SAR backscatter thresholding (VV < -16 dB). Future releases will incorporate multi-temporal coherence change detection.
- **Offline Mesh Networking:** In severe infrastructure failures where cellular data collapses, ground SOS reports rely on local offline storage until connectivity is restored. Future releases will integrate Bluetooth Low Energy (BLE) peer mesh routing and LoRa gateway forwarders.
- **Real-Time Edge Drone Feeds:** Extending the ONNX inference pipeline to accept low-altitude uncrewed aerial vehicle (UAV) video streams for near-instant casualty and road blockage validation.
