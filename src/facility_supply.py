"""Link unreviewed facility candidates to whole-route record composition."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from src.distance_reference import geodesic_metres
from src.facility_catchments import RADII, address_check, point

from src.route_records import aggregate_routes


THRESHOLDS=(.3,.5,.8)


def link_supply(facilities,edges,route_days):
    supply=aggregate_routes(route_days)
    stations={}
    station_routes=defaultdict(set)
    for edge in edges:
        identifier=edge['station_id']
        coordinate=point(edge)
        if not identifier or not edge['route_id'] or coordinate is None:
            raise ValueError('Invalid station identity or coordinate')
        if identifier in stations and stations[identifier]!=coordinate:
            raise ValueError('Inconsistent station coordinate')
        stations[identifier]=coordinate
        station_routes[identifier].add(edge['route_id'])
    if not stations:
        raise ValueError('No candidate stations')
    by_radius={r:dict(radius_metres=r,facilities_with_nearby_route=0,no_nearby_route=0,
                      facilities_with_missing_route_records=0,
                      threshold_checks=[dict(threshold=t,lower_bound_meets=0,upper_bound_below=0,uncertain=0)
                                        for t in THRESHOLDS]) for r in RADII}
    route_facilities=defaultdict(lambda:{r:set() for r in RADII})
    seen=set();details=[];matching=0
    for row in facilities:
        identifier=row['facility_id']
        if not identifier or identifier in seen:
            raise ValueError('Empty or duplicate facility ID')
        seen.add(identifier)
        coordinate=point(row)
        if row['review_status']!='candidate_unreviewed' or coordinate is None or address_check(row)!='road_building_match_unreviewed':
            continue
        matching+=1
        detail=dict(row)
        distances=[(geodesic_metres(coordinate,location),station) for station,location in stations.items()]
        for radius in RADII:
            routes={route for distance,station in distances if distance<=radius for route in station_routes[station]}
            group=by_radius[radius]
            tag=str(radius)
            detail['nearby_routes_'+tag]=len(routes)
            detail['route_ids_'+tag]=';'.join(sorted(routes))
            if not routes:
                group['no_nearby_route']+=1
                detail['best_route_share_lower_'+tag]=None
                detail['best_route_share_upper_'+tag]=None
                continue
            group['facilities_with_nearby_route']+=1
            missing={route for route in routes if route not in supply or not supply[route]['records']}
            known=routes-missing
            lower=max((supply[route]['lower'] for route in known),default=0)
            upper=max([supply[route]['upper'] for route in known]+([1] if missing else []))
            detail['best_route_share_lower_'+tag]=lower
            detail['best_route_share_upper_'+tag]=upper
            detail['missing_route_records_'+tag]=len(missing)
            group['facilities_with_missing_route_records']+=int(bool(missing))
            for check in group['threshold_checks']:
                category=('lower_bound_meets' if lower>=check['threshold'] else
                          'upper_bound_below' if upper<check['threshold'] else 'uncertain')
                check[category]+=1
            for route in routes:
                route_facilities[route][radius].add(identifier)
        details.append(detail)
    route_ids=set().union(*station_routes.values())
    route_results=[]
    for identifier in sorted(route_ids):
        values=supply.get(identifier,dict(route_name='',records=0,low_floor_records=0,
                                        regular_records=0,unknown_records=0,lower=None,upper=None,dates=[]))
        route_results.append(dict(route_id=identifier,**values,
                                  matching_candidate_facilities_by_radius={str(r):len(route_facilities[identifier][r]) for r in RADII}))
    return dict(source_facilities=len(seen),address_matching_candidate_facilities=matching,
                excluded_or_not_address_matching=len(seen)-matching,
                reviewed_buildings=0,verified_local_low_floor_service=False,
                by_radius=list(by_radius.values()),by_route=route_results,
                thresholds_note='30%, 50%, 80% are diagnostic sensitivity thresholds, not policy standards or service guarantees.',
                warning='Whole-route operation-record shares, not observed arrivals at nearby stations. Current vehicle classifications are conditionally linked to historical records. Facilities remain unreviewed. For each facility, max route lower and max route upper bound the best whole-route record composition; the maxima can come from different routes. Unknown route data contribute [0,1]. Nearby routes may not serve the same destinations or direction and cannot be assumed interchangeable. Facility counts are not passenger demand, waiting time, carbon savings or verified accessibility. Route facility counts overlap and must not be summed.'),details


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facilities',required=True)
    parser.add_argument('--edges',required=True)
    parser.add_argument('--supply',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--details-output',required=True)
    args=parser.parse_args()
    paths=[Path(v).resolve() for v in [args.facilities,args.edges,args.supply,args.output,args.details_output]]
    if len(set(paths))!=len(paths):
        raise ValueError('Inputs and outputs must use distinct paths')
    target=Path(args.details_output)
    if target.exists():
        raise ValueError('Choose a new details path to preserve reviews')
    def read(path):
        with Path(path).open(encoding='utf-8-sig',newline='') as stream:
            return list(csv.DictReader(stream))
    summary,details=link_supply(read(args.facilities),read(args.edges),
                                json.loads(Path(args.supply).read_text(encoding='utf-8'))['by_route_day'])
    if not details:
        raise ValueError('No address-matching facility candidates')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8-sig',newline='') as stream:
        fields=list(dict.fromkeys(key for row in details for key in row))
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(details)
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='by_route'},ensure_ascii=True))
