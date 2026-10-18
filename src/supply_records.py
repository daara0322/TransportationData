"""Summarize operation records without treating them as verified full trips."""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from src.audit_operations import clean


COUNT_FIELDS = ['records', 'low_floor_records', 'regular_records', 'unknown_records',
                'distance_positive_records', 'distance_zero_records',
                'distance_negative_records', 'distance_missing_records',
                'distance_invalid_records', 'same_endpoint_records']


def finalize(counts):
    result = {key: counts[key] for key in COUNT_FIELDS}
    total = result['records']
    result['classification_record_coverage'] = ((total-result['unknown_records'])/total
                                                if total else None)
    result['low_floor_record_share_lower_bound'] = result['low_floor_records']/total if total else None
    result['low_floor_record_share_upper_bound'] = ((result['low_floor_records']+result['unknown_records'])/total
                                                    if total else None)
    return result


def summarize_supply(rows, snapshot, route_audit):
    eligible, exclusions = {}, Counter()
    for route in route_audit['routes']:
        if not route['master_found']:
            exclusions['missing_master'] += 1
        elif route['candidate_name'] != route['master_name']:
            exclusions['name_mismatch'] += 1
        elif route['route_type'] not in ['3', '4']:
            exclusions['other_route_type'] += 1
        else:
            eligible[route['route_id']] = route
    types = defaultdict(set)
    for item in snapshot['records']:
        if item['low_floor'] is not None:
            types[(item['route_id'], item['vehicle_id'])].add(item['low_floor'])
    known = {pair: next(iter(values)) for pair, values in types.items() if len(values) == 1}
    by_route_day, by_type_day, by_day = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    totals, seen = Counter(), set()
    source_rows = outside = duplicates = invalid_identity = 0
    for raw in rows:
        row = {clean(k): clean(v) for k, v in raw.items() if k is not None}
        source_rows += 1
        route_id = row.get('노선ID', '')
        if route_id not in eligible:
            outside += 1
            continue
        keys = ['기준일', '노선ID', '버스ID', '운행순번', 'SSTTN_DT']
        identity = tuple(row.get(key, '') for key in keys)
        if not all(identity):
            invalid_identity += 1
            continue
        try:
            if len(row['기준일']) != 8:
                raise ValueError('Invalid date')
            datetime.strptime(row['기준일'], '%Y%m%d')
        except ValueError:
            invalid_identity += 1
            continue
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        meta = eligible[route_id]
        day, route_type = row['기준일'], meta['route_type']
        group = 'night_name' if meta['candidate_name'].startswith('N') else 'other_daytime_or_custom'
        value = known.get((route_id, row['버스ID']))
        class_field = 'low_floor_records' if value is True else 'regular_records' if value is False else 'unknown_records'
        distance = row.get('운행거리', '')
        if not distance:
            dist_field = 'distance_missing_records'
        else:
            try:
                number = float(distance)
                dist_field = ('distance_invalid_records' if not math.isfinite(number) else
                              'distance_negative_records' if number < 0 else
                              'distance_zero_records' if number == 0 else 'distance_positive_records')
            except ValueError:
                dist_field = 'distance_invalid_records'
        same_endpoints = bool(row.get('출발정류장ID') and row.get('출발정류장ID') == row.get('최종정류장ID'))
        for counts in [totals, by_route_day[(route_id, day)], by_type_day[(route_type, group, day)], by_day[day]]:
            counts['records'] += 1
            counts[class_field] += 1
            counts[dist_field] += 1
            counts['same_endpoint_records'] += int(same_endpoints)
    route_days = []
    for (route_id, day), counts in sorted(by_route_day.items()):
        meta = eligible[route_id]
        route_days.append(dict(route_id=route_id, route_name=meta['candidate_name'],
                               route_type=meta['route_type'], date=day,
                               service_group='night_name' if meta['candidate_name'].startswith('N') else 'other_daytime_or_custom',
                               **finalize(counts)))
    return dict(source_rows=source_rows, eligible_routes=len(eligible),
                scope_excluded_route_counts=dict(exclusions), outside_scope_rows=outside,
                duplicate_candidate_rows_excluded=duplicates, invalid_identity_rows_excluded=invalid_identity,
                eligible_routes_without_records=sorted(set(eligible)-{key[0] for key in by_route_day}),
                totals=finalize(totals), by_route_day=route_days,
                by_type_day=[dict(route_type=t, service_group=g, date=d, **finalize(c))
                             for (t, g, d), c in sorted(by_type_day.items())],
                by_day=[dict(date=d, **finalize(c)) for d, c in sorted(by_day.items())],
                warning='Operation records are not verified full trips or passengers. Current vehicle types are only conditionally applicable historically. Bounds are neither confidence intervals nor observed waiting times. Distances remain in unverified source units; zero and negative rows remain flagged in the denominator.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operations', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--route-audit', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text(encoding='utf-8-sig'))
    audit = json.loads(Path(args.route_audit).read_text(encoding='utf-8-sig'))
    with Path(args.operations).open(encoding='utf-8-sig', newline='') as stream:
        result = summarize_supply(csv.DictReader(stream), snapshot, audit)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if not k.startswith('by_') and k != 'warning'}, ensure_ascii=True))
