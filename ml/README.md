# ml/ — damage assessment

Models and scripts that turn imagery into `BuildingAssessment` and `ZoneAssessment`
records (shapes defined once, in `backend/schemas/contracts.py`).

Planned contents (final version):

- `train_xbd.py` — building damage classifier trained on xBD (CC BY-NC-SA 4.0; Gupta et al. 2019)
- `flood_sen1floods11.py` — flood extent from Sen1Floods11
- `aggregate_zones.py` — buildings → zones (OpenStreetMap boundaries, WorldPop population)
- `notebooks/` — exploration

Until a trained model is wired in, `simulate_assessments.py` produces assessments with
`source="simulated"` from a scenario in `data/scenarios/`, so the rest of the pipeline can run.
Every output carries its `source` so the UI can state what is real and what is simulated.
