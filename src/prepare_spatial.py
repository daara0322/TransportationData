"""Prepare deduplicated route/station edges for future catchment analysis."""
import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

from src.audit_route_master import read_csv


def prepare_edges(nodes, stations, eligible):
    master = {}
    for station in stations:
        identifier = station['정류장ID']
        if not identifier or identifier in master:
            raise ValueError('Duplicate station ID or empty ID')
        master[identifier] = station
    counts, seen, edges = Counter(), set(), []
    for node in nodes:
        if node['노선ID'] not in eligible:
            continue
        counts['eligible_node_rows'] += 1
        if node.get('사용여부') != '1':
            counts['inactive_node_rows'] += 1
            continue
        station = master.get(node['노드ID'])
        if station is None:
            counts['nodes_not_in_station_master'] += 1
            continue
        if station.get('정류장이용여부') != '1':
            counts['inactive_station_nodes'] += 1
            continue
        if station.get('가상정류장여부') != '0':
            counts['virtual_station_nodes'] += 1
            continue
        try:
            x, y = float(station['좌표X']), float(station['좌표Y'])
            if not (math.isfinite(x) and math.isfinite(y) and 124<=x<=132 and 33<=y<=40):
                raise ValueError('Coordinate outside broad study check')
        except (ValueError, KeyError):
            counts['invalid_coordinate_nodes'] += 1
            continue
        pair = (node['노선ID'], station['정류장ID'])
        if pair in seen:
            counts['duplicate_edges'] += 1
            continue
        seen.add(pair)
        edges.append(dict(route_id=pair[0], station_id=pair[1],
                          station_name=station['정류장명'], longitude=x, latitude=y))
    required = ['eligible_node_rows', 'inactive_node_rows', 'nodes_not_in_station_master',
                'inactive_station_nodes', 'virtual_station_nodes', 'invalid_coordinate_nodes', 'duplicate_edges']
    audit = {field: counts[field] for field in required}
    audit.update(route_station_edges=len(edges), unique_stations=len({e['station_id'] for e in edges}),
                 routes_with_stations=len({e['route_id'] for e in edges}),
                 eligible_routes_without_stations=sorted(eligible-{e['route_id'] for e in edges}),
                 coordinate_check='124..132 longitude, 33..40 latitude; broad plausibility check, not a Seoul boundary',
                 warning='Unique route/station edges discard route order and direction; do not use as directed paths or sum repeated station catchments.')
    return sorted(edges, key=lambda e:(e['route_id'],e['station_id'])), audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nodes', required=True)
    parser.add_argument('--stations', required=True)
    parser.add_argument('--route-audit', required=True)
    parser.add_argument('--edges-output', required=True)
    parser.add_argument('--audit-output', required=True)
    args = parser.parse_args()
    routes = json.loads(Path(args.route_audit).read_text(encoding='utf-8-sig'))['routes']
    eligible = {r['route_id'] for r in routes if r['master_found'] and
                r['master_name']==r['candidate_name'] and r['route_type'] in ['3','4']}
    edges, audit = prepare_edges(read_csv(args.nodes), read_csv(args.stations), eligible)
    target = Path(args.edges_output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['route_id','station_id','station_name','longitude','latitude'])
        writer.writeheader()
        writer.writerows(edges)
    audit_target = Path(args.audit_output)
    audit_target.parent.mkdir(parents=True, exist_ok=True)
    audit_target.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(audit, ensure_ascii=True))
