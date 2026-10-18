"""Diagnose unreviewed facility coordinates against candidate route stations."""
import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from src.distance_reference import geodesic_metres


RADII=(300,500,800)
ROAD_BUILDING=re.compile(r'(?:^|\s)([^\s,()]+(?:대로|로|길))\s+(\d+(?:-\d+)?)(?=$|[\s,(])')


def validate_paths(facilities,edges,summary,details):
    paths=[Path(value).resolve() for value in [facilities,edges,summary,details]]
    if len(set(paths))!=len(paths):
        raise ValueError('Inputs, summary and review output must use distinct paths')


def address_check(row):
    a=ROAD_BUILDING.search(row['address'])
    b=ROAD_BUILDING.search(row['matched_address'])
    if not a or not b:
        return 'not_comparable'
    return 'road_building_match_unreviewed' if a.groups()==b.groups() else 'road_building_mismatch'


def point(row):
    try:
        x,y=float(row['longitude']),float(row['latitude'])
        if math.isfinite(x) and math.isfinite(y) and 124<=x<=132 and 33<=y<=40:
            return x,y
    except (ValueError,TypeError,KeyError):
        pass
    return None


def diagnose(facilities,edges):
    stations={}
    routes=defaultdict(set)
    for edge in edges:
        identifier=edge['station_id']
        coordinate=point(edge)
        if not coordinate:
            raise ValueError('Invalid station coordinate')
        if identifier in stations and stations[identifier]!=coordinate:
            raise ValueError('Inconsistent coordinates for one station')
        stations[identifier]=coordinate
        routes[identifier].add(edge['route_id'])
    if not stations:
        raise ValueError('No stations supplied')
    seen=set()
    counts=Counter()
    global_sets={r:set() for r in RADII}
    matching_sets={r:set() for r in RADII}
    route_sets=defaultdict(lambda:{r:set() for r in RADII})
    route_matching=defaultdict(lambda:{r:set() for r in RADII})
    details=[]
    for row in facilities:
        identifier=row['facility_id']
        if not identifier or identifier in seen:
            raise ValueError('Empty or duplicate facility ID')
        seen.add(identifier)
        result=dict(row,address_check='not_tested',nearest_station_id='',nearest_station_metres='')
        coordinate=point(row)
        if row['review_status']!='candidate_unreviewed' or coordinate is None:
            counts['excluded_'+row['review_status'] if coordinate is not None else 'excluded_no_valid_coordinate']+=1
            details.append(result)
            continue
        check=address_check(row)
        result['address_check']=check
        if check=='not_comparable' and re.search(r'(?:대로|로|길)\s*$', row['matched_address']):
            result['address_check']='incomplete_road_address'
            counts['incomplete_road_address']+=1
            details.append(result)
            continue
        counts['usable_candidate_points']+=1
        counts[check]+=1
        distances=[(geodesic_metres(coordinate,location),station) for station,location in stations.items()]
        nearest,nearest_id=min(distances)
        result.update(nearest_station_id=nearest_id,nearest_station_metres=round(nearest,2))
        for radius in RADII:
            nearby=[station for distance,station in distances if distance<=radius]
            result['nearby_unique_stations_'+str(radius)]=len(nearby)
            if nearby:
                global_sets[radius].add(identifier)
                if check=='road_building_match_unreviewed':
                    matching_sets[radius].add(identifier)
            for route in {route for station in nearby for route in routes[station]}:
                route_sets[route][radius].add(identifier)
                if check=='road_building_match_unreviewed':
                    route_matching[route][radius].add(identifier)
        details.append(result)
    summary=dict(source_facilities=len(seen),usable_candidate_points=counts['usable_candidate_points'],
                 reviewed_buildings=0,confirmed_accessibility_analysis=False,
                 unique_candidate_stations=len(stations),candidate_routes=len(set().union(*routes.values())),
                 coordinate_and_address_checks=dict(counts),
                 by_radius=[dict(radius_metres=r,candidate_facilities_near_any_station=len(global_sets[r]),
                                 road_building_matching_candidates_near_any_station=len(matching_sets[r])) for r in RADII],
                 by_route=[dict(route_id=route,candidate_facilities_by_radius={str(r):len(route_sets[route][r]) for r in RADII},
                                road_building_matching_candidates_by_radius={str(r):len(route_matching[route][r]) for r in RADII})
                           for route in sorted(set().union(*routes.values()))],
                 warning='Unreviewed coordinate sensitivity only, not verified accessibility, walking routes, passenger demand, or low-floor service. Road/building string agreement is not a building inspection. Each facility counted once per route/radius and once in global coverage; route counts overlap and must not be summed. Stations cover the selected 375-route scope, not every bus route.')
    return summary,details


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facilities',required=True)
    parser.add_argument('--edges',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--details-output',required=True)
    args=parser.parse_args()
    validate_paths(args.facilities,args.edges,args.output,args.details_output)
    def read(path):
        with Path(path).open(encoding='utf-8-sig',newline='') as stream:
            return list(csv.DictReader(stream))
    summary,details=diagnose(read(args.facilities),read(args.edges))
    target=Path(args.details_output)
    if target.exists():
        raise ValueError('Choose a new details path to preserve manual review')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8-sig',newline='') as stream:
        fields=list(dict.fromkeys(key for row in details for key in row))
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader();writer.writerows(details)
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='by_route'},ensure_ascii=True))
