"""Check dispatch-history semantics before any observed headway calculation."""
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from src.audit_route_master import read_csv


KEYS = ['기준일', '노선ID', '운행순번', '운행계획ID']


def key(row):
    return tuple(row[name] for name in KEYS)


def delta(end, start):
    return int((datetime.strptime(end, '%Y%m%d%H%M%S') -
                datetime.strptime(start, '%Y%m%d%H%M%S')).total_seconds())


def audit_dispatch(station_rows, vehicle_rows):
    groups, steps, dwell = defaultdict(list), Counter(), Counter()
    invalid_sequence = invalid_pairs = invalid_dwell = constant_groups = 0
    for row in station_rows:
        try:
            seq = int(row['정류장순번'])
        except ValueError:
            invalid_sequence += 1
            continue
        groups[key(row)].append((seq, row))
    for values in groups.values():
        values.sort(key=lambda pair: pair[0])
        group_steps = []
        for (_, a), (_, b) in zip(values, values[1:]):
            try:
                seconds = delta(b['도착일시'], a['도착일시'])
                steps[str(seconds)] += 1
                group_steps.append(seconds)
            except ValueError:
                invalid_pairs += 1
        if len(values) >= 3 and len(group_steps) == len(values)-1 and len(set(group_steps)) == 1:
            constant_groups += 1
    for row in station_rows:
        try:
            dwell[str(delta(row['출발일시'], row['도착일시']))] += 1
        except ValueError:
            invalid_dwell += 1
    vehicle_keys = [key(row) for row in vehicle_rows]
    total_steps = sum(steps.values())
    return dict(station_rows=len(station_rows), vehicle_rows=len(vehicle_rows),
                station_dates=dict(Counter(row['기준일'] for row in station_rows)),
                vehicle_dates=dict(Counter(row['기준일'] for row in vehicle_rows)),
                station_routes=len({row['노선ID'] for row in station_rows}),
                vehicle_routes=len({row['노선ID'] for row in vehicle_rows}),
                station_run_groups=len(groups), vehicle_unique_run_keys=len(set(vehicle_keys)),
                vehicle_duplicate_run_keys=len(vehicle_keys)-len(set(vehicle_keys)),
                matched_station_groups=len(set(groups) & set(vehicle_keys)),
                adjacent_arrival_differences_seconds=dict(steps),
                departure_minus_arrival_seconds=dict(dwell),
                backward_adjacent_arrivals=sum(count for seconds, count in steps.items() if int(seconds)<0),
                whole_minute_adjacent_steps=sum(count for seconds, count in steps.items() if int(seconds)%60==0),
                valid_adjacent_steps=total_steps,
                invalid_station_sequence_rows=invalid_sequence,
                invalid_adjacent_time_pairs=invalid_pairs, invalid_dwell_rows=invalid_dwell,
                constant_interval_groups_with_at_least_three_rows=constant_groups,
                observed_headway_analysis_ready=False,
                decision='Schedule versus actual timestamp semantics must be verified externally. This diagnostic never certifies observed headways or passenger waiting times.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stations', required=True)
    parser.add_argument('--vehicles', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit_dispatch(read_csv(args.stations), read_csv(args.vehicles))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
