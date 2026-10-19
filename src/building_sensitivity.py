"""Compare two unreviewed address points for one reference facility."""
import argparse
import csv
import json
from pathlib import Path

from src.distance_reference import geodesic_metres
from src.facility_catchments import RADII, address_check, point
from src.facility_supply import aggregate_routes, link_supply


def compare_candidates(reference_id,candidates,edges,route_days):
    identifiers=[row['facility_id'] for row in candidates]
    if not reference_id or len(candidates)!=2 or len(set(identifiers))!=2:
        raise ValueError('Exactly two unique address scenarios for one reference are required')
    for row in candidates:
        if not row['facility_id'].startswith(reference_id+'_') or not row['facility_id'].endswith('_scenario'):
            raise ValueError('Scenario ID does not belong to the reference facility')
        if row['review_status']!='candidate_unreviewed' or point(row) is None or address_check(row)!='road_building_match_unreviewed':
            raise ValueError('Both address points must be valid unreviewed building-address candidates')
    _,details=link_supply(candidates,edges,route_days)
    supply=aggregate_routes(route_days)
    station_routes={}
    for edge in edges:
        station_routes.setdefault(edge['route_id'],{})[edge['station_id']]=point(edge)
    comparisons=[]
    for row in details:
        coordinate=point(row)
        distances={route:min(geodesic_metres(coordinate,location) for location in stops.values())
                   for route,stops in station_routes.items()}
        nearby=[]
        for radius in RADII:
            entries=[dict(route_id=route,route_name=supply.get(route,{}).get('route_name',''),
                          nearest_station_metres=round(distance,3))
                     for route,distance in sorted(distances.items()) if distance<=radius]
            nearby.append(dict(radius_metres=radius,nearby_routes=len(entries),routes=entries,
                               best_route_share_lower=row['best_route_share_lower_'+str(radius)],
                               best_route_share_upper=row['best_route_share_upper_'+str(radius)]))
        comparisons.append(dict(scenario_id=row['facility_id'],query_address=row['address'],by_radius=nearby))
    return dict(reference_facility_id=reference_id,reference_facilities=1,scenario_count=2,
                coordinate_separation_metres=round(geodesic_metres(point(candidates[0]),point(candidates[1])),3),
                verified_building_or_entrance=False,scenarios=comparisons,
                warning='Two address scenarios for ONE facility; do not add them to facility totals. Candidate coordinates are not entrance or walking-route inspections. Whole-route historical record composition remains conditional on current vehicle classification. A radius-threshold change is model sensitivity, not proof of actual access disparity, demand or carbon benefit. The annex address is a reported alternative that requires independent site confirmation.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-id',required=True)
    parser.add_argument('--candidates',required=True)
    parser.add_argument('--edges',required=True)
    parser.add_argument('--supply',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    paths=[Path(p).resolve() for p in [args.candidates,args.edges,args.supply,args.output]]
    if len(set(paths))!=len(paths):raise ValueError('Inputs and output must use distinct paths')
    def read(path):
        with Path(path).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))
    result=compare_candidates(args.reference_id,read(args.candidates),read(args.edges),
                              json.loads(Path(args.supply).read_text(encoding='utf-8'))['by_route_day'])
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='scenarios'},ensure_ascii=True))
