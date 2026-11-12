"""Before/after report: utilisation per resource, coverage per level and per type, Gini, time."""
import importlib.util
import sys
import time

import numpy as np

sys.path.insert(0, '.')
from services.scenarios import RESOURCE_TYPES, get_scenario  # noqa: E402

IDS = ['flood-aluva', 'flood-bengaluru', 'cyclone-visakhapatnam', 'earthquake-coimbatore']
LEVELS = ('Critical', 'High', 'Medium', 'Low')


def load(label, path):
    spec = importlib.util.spec_from_file_location(f"engine_{label}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def report(engine, scenario_id, runs=2):
    s = get_scenario(scenario_id)
    engine.allocate(s)  # warm
    best, r = 1e9, None
    for _ in range(runs):
        t = time.perf_counter()
        r = engine.allocate(s)
        best = min(best, time.perf_counter() - t)
    zones = r['zones']
    stock = r['resources']
    alloc = {k: sum(z['engine']['allocated'][k] for z in zones) for k in RESOURCE_TYPES}
    demand = {k: sum(z['demand'][k] for z in zones) for k in RESOURCE_TYPES}
    util = {k: f"{alloc[k]}/{stock[k]}" + ("" if alloc[k] == min(stock[k], demand[k]) else " IDLE") for k in RESOURCE_TYPES}
    by_level = {}
    per_type = {}
    for lv in LEVELS:
        zs = [z for z in zones if z['priority_level'] == lv and z['engine']['coverage_pct'] is not None]
        if not zs:
            continue
        by_level[lv] = round(float(np.mean([z['engine']['coverage_pct'] for z in zs])), 1)
        per_type[lv] = {}
        for k in RESOURCE_TYPES:
            d = sum(z['demand'][k] for z in zs)
            a = sum(min(z['engine']['allocated'][k], z['demand'][k]) for z in zs)
            per_type[lv][k] = round(a / d * 100, 1) if d else None
    m = r['engine']['metrics']
    print(f"  {scenario_id:24} cov {m['coverage_pct']:5}  gini {m['gini']:<6} within {m.get('gini_within_level')}  time {best:4.1f}s")
    print(f"    levels {by_level}")
    print(f"    util   {util}")
    for lv, row in per_type.items():
        print(f"    {lv:9} " + "  ".join(f"{k[:7]}={v}" for k, v in row.items()))
    return r


if __name__ == '__main__':
    for label, path in [a.split('=') for a in sys.argv[1:]]:
        print(f"== {label}")
        eng = load(label, path)
        for i in IDS:
            report(eng, i)
