"""Cross-check candidate routes against independently downloaded master files."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from src.audit_operations import clean


def clean_row(row):
    return {clean(k): clean(v) for k, v in row.items() if k is not None}


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return [clean_row(row) for row in csv.DictReader(stream)]


def summarize_master(master_rows, candidates, linkage, snapshot, vehicle_routes):
    master = {}
    for raw in master_rows:
        row = clean_row(raw)
        route_id = row['노선ID']
        if not route_id or route_id in master:
            raise ValueError('Duplicate master route ID or empty ID')
        master[route_id] = row
    candidate_types, candidate_regions = Counter(), Counter()
    missing, mismatches, routes = [], [], []
    linked = {row['route_id']: row for row in linkage['routes']}
    for route_id, name in sorted(candidates.items()):
        row = master.get(route_id)
        if row is None:
            missing.append(route_id)
        elif row['노선명'] != name:
            mismatches.append(dict(route_id=route_id, candidate_name=name,
                                   master_name=row['노선명']))
        candidate_types[row.get('노선유형', '') if row else 'missing'] += 1
        candidate_regions[row.get('지역ID', '') if row else 'missing'] += 1
        item = dict(route_id=route_id, candidate_name=name,
                    master_found=row is not None,
                    master_name=row.get('노선명') if row else None,
                    route_type=row.get('노선유형') if row else None,
                    region_code=row.get('지역ID') if row else None,
                    master_use_flag=row.get('사용여부') if row else None,
                    master_operating_flag=row.get('운행여부') if row else None,
                    low_floor_share_lower_bound=None,
                    low_floor_share_upper_bound=None)
        history = linked.get(route_id)
        if history is not None:
            total = history['historical_vehicles']
            low, regular = history['low_floor_vehicles'], history['regular_vehicles']
            unknown, classified = history['unclassified_vehicles'], history['classified_vehicles']
            if (min(total, low, regular, unknown, classified) < 0 or
                    low + regular != classified or classified + unknown != total):
                raise ValueError('Inconsistent classification counts')
            if total:
                item['low_floor_share_lower_bound'] = low / total
                item['low_floor_share_upper_bound'] = (low + unknown) / total
        routes.append(item)
    pairs = {(clean(row['노선ID']), clean(row['차량ID'])) for row in vehicle_routes}
    observed = {(row['route_id'], row['vehicle_id']) for row in snapshot['records']}
    return dict(master_rows=len(master_rows), master_unique_ids=len(master),
                candidate_count=len(candidates), missing_master_ids=missing,
                name_mismatches=mismatches,
                candidate_type_counts=dict(sorted(candidate_types.items())),
                candidate_region_counts=dict(sorted(candidate_regions.items())),
                vehicle_master_rows=len(vehicle_routes), vehicle_master_unique_pairs=len(pairs),
                snapshot_unique_pairs=len(observed),
                snapshot_pairs_in_vehicle_master=len(observed & pairs),
                snapshot_pairs_not_in_vehicle_master=len(observed - pairs),
                routes=routes,
                warning='Bounds concern historical route/vehicle pairs conditional on current classifications being valid historically. They are not trip shares, confidence intervals, or a fleet census. Region codes are not decoded here.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', required=True)
    parser.add_argument('--vehicle-routes', required=True)
    parser.add_argument('--candidates', required=True)
    parser.add_argument('--linkage', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    def read_json(path):
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    result = summarize_master(read_csv(args.master), read_json(args.candidates)['routes'],
                              read_json(args.linkage), read_json(args.snapshot),
                              read_csv(args.vehicle_routes))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ['routes', 'warning']}, ensure_ascii=True))
