"""Print the README results table (Allocation Engine vs greedy) for every scenario."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import allocation_engine as engine  # noqa: E402
from services.scenarios import get_scenario, list_scenarios  # noqa: E402

print("| Scenario | Method | Avg response | Weighted coverage | Demand met | Unmet demand | Gini | Zones reached | Time |")
print("|---|---|---|---|---|---|---|---|---|")
for s in list_scenarios():
    started = time.perf_counter()
    r = engine.allocate(get_scenario(s.id))
    seconds = time.perf_counter() - started
    for label, key, t in (("Allocation Engine", "engine", f"{seconds:.1f} s"), ("Greedy", "greedy", f"{r['greedy']['metrics']['computation_ms']:.1f} ms")):
        m = r[key]["metrics"]
        first = f"`{s.id}`" if key == "engine" else ""
        print(f"| {first} | {label} | {m['avg_response_time_min']:.1f} min | {m['coverage_pct']:.1f} % | {m['demand_met_pct']:.1f} % | "
              f"{m['unmet_demand_pct']:.1f} % | {m['gini']:.3f} | {m['zones_served']} / {m['zones_in_need']} | {t} |")
