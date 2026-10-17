"""Audit a current classification snapshot against historical route/vehicle pairs."""
import argparse
import csv
import json
from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path
from src.audit_operations import clean


def summarize_linkage(source, snapshot):
    route_status = {s['route_id']: s['status'] for s in snapshot['statuses']}
    types = defaultdict(set)
    current = defaultdict(set)
    for record in snapshot['records']:
        pair = (record['route_id'], record['vehicle_id'])
        current[pair[0]].add(pair[1])
        value = record['low_floor']
        if value is not None:
            types[pair].add(value)
    classifications = {pair: next(iter(values)) for pair, values in types.items() if len(values) == 1}
    vehicles, counts, names = defaultdict(set), defaultdict(int), defaultdict(set)
    context = (Path(source).open(encoding='utf-8-sig', newline='')
               if isinstance(source, (str, Path)) else nullcontext(source))
    with context as stream:
        for raw in csv.DictReader(stream):
            row = {clean(k): clean(v) for k, v in raw.items() if k is not None}
            route = row['노선ID']
            if route not in route_status:
                continue
            if row['버스ID']:
                vehicles[route].add(row['버스ID'])
            names[route].add(row.get('노선명', ''))
            counts[route] += 1
    results = []
    for route in sorted(route_status):
        history = vehicles[route]
        low = sum(classifications.get((route, vehicle)) is True for vehicle in history)
        regular = sum(classifications.get((route, vehicle)) is False for vehicle in history)
        classified = low + regular
        results.append(dict(route_id=route, route_names=sorted(names[route]),
                            api_status=route_status[route], current_vehicles=len(current[route]),
                            historical_rows=counts[route], historical_vehicles=len(history),
                            matched_vehicles=len(history & current[route]),
                            classified_vehicles=classified, low_floor_vehicles=low,
                            regular_vehicles=regular, unclassified_vehicles=len(history)-classified,
                            classification_coverage=classified/len(history) if history else None))
    return dict(routes=results, conflicting_pairs=sum(len(v)>1 for v in types.values()),
                warning='Current classification is not verified historical classification; purposeful sample, not a fleet census.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operations', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text(encoding='utf-8-sig'))
    result = summarize_linkage(args.operations, snapshot)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
