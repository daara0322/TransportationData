"""Check operation distances against route reference distances and coordinates."""
import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from src.audit_operations import clean
from src.audit_route_master import read_csv


def finite(value):
    try:
        value=float(value)
        return value if math.isfinite(value) else None
    except (ValueError,TypeError):
        return None


def distribution(values):
    if not values:
        return dict(count=0,p10=None,median=None,p90=None)
    values=sorted(values)
    return dict(count=len(values),p10=values[int((len(values)-1)*.1)],
                median=statistics.median(values),p90=values[int((len(values)-1)*.9)])


def audit_reference(rows,nodes,eligible):
    index=defaultdict(set)
    for node in nodes:
        value=finite(node['구간거리누계'])
        if node['노선ID'] in eligible and value is not None:
            index[(node['노선ID'],node['노드순번'],node['노드ID'])].add(value)
    totals,by_route=Counter(),defaultdict(Counter)
    differences=[]
    for raw in rows:
        row={clean(k):clean(v) for k,v in raw.items() if k is not None}
        route=row['노선ID']
        if route not in eligible:
            continue
        flags=Counter(included_records=1)
        reported=finite(row.get('운행거리'))
        if reported is None:
            flags['reported_missing_or_invalid_records']=1
        else:
            flags['reported_negative_records' if reported<0 else
                  'reported_zero_records' if reported==0 else 'reported_positive_records']=1
            if reported==0 and row['출발정류장ID']==row['최종정류장ID']:
                flags['reported_zero_same_endpoint_records']=1
        a=index.get((route,row['출발정류장순번'],row['출발정류장ID']),set())
        b=index.get((route,row['최종정류장순번'],row['최종정류장ID']),set())
        if not a or not b:
            flags['missing_reference_records']=1
        elif len(a)!=1 or len(b)!=1:
            flags['ambiguous_reference_records']=1
        else:
            flags['unique_reference_records']=1
            delta=next(iter(b))-next(iter(a))
            if reported is not None:
                diff=reported-delta
                differences.append(diff)
                if abs(diff)<=1:
                    flags['reported_matches_reference_within_one_source_unit']=1
                if reported<0 and delta<0:
                    flags['negative_with_decreasing_reference']=1
        totals.update(flags)
        by_route[route].update(flags)
    fields=['included_records','reported_positive_records','reported_zero_records',
            'reported_negative_records','reported_missing_or_invalid_records',
            'reported_zero_same_endpoint_records','unique_reference_records',
            'missing_reference_records','ambiguous_reference_records',
            'reported_matches_reference_within_one_source_unit','negative_with_decreasing_reference']
    return dict(**{k:totals[k] for k in fields},
                reported_minus_reference_source_units=distribution(differences),
                by_route=[dict(route_id=route,**{k:counts[k] for k in fields})
                          for route,counts in sorted(by_route.items())],
                warning='Reference differences use the downloaded current route nodes. Agreement does not prove odometer measurements, complete trips, official units, or historical route validity. Distances are not corrected.')


def geodesic_metres(a,b):
    lon1,lat1,lon2,lat2=map(math.radians,(*a,*b))
    h=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 2*6371008.8*math.asin(math.sqrt(min(1,max(0,h))))


def coordinate_check(nodes,stations,eligible):
    coords={}
    for station in stations:
        identifier=station['정류장ID']
        if identifier in coords:
            raise ValueError('Duplicate station ID')
        x,y=finite(station.get('좌표X')),finite(station.get('좌표Y'))
        coords[identifier]=(x,y) if x is not None and y is not None and 124<=x<=132 and 33<=y<=40 else None
    routes=defaultdict(lambda:defaultdict(set))
    for node in nodes:
        if node['노선ID'] not in eligible or coords.get(node['노드ID']) is None:
            continue
        d=finite(node['구간거리누계'])
        try:seq=int(node['노드순번'])
        except ValueError:continue
        if d is not None:
            routes[node['노선ID']][seq].add((node['노드ID'],d))
    ratios=[]
    skipped=Counter()
    for route,sequence in routes.items():
        values=[]
        for seq,items in sorted(sequence.items()):
            if len(items)!=1:
                skipped['ambiguous_station_positions']+=1
                continue
            identifier,d=next(iter(items));values.append((identifier,d))
        for (a,da),(b,db) in zip(values,values[1:]):
            chord=geodesic_metres(coords[a],coords[b])
            if chord<=0 or db<=da:
                skipped['nonpositive_reference_or_geodesic_segments']+=1
                continue
            ratios.append((db-da)/chord)
    return dict(positive_local_segments=len(ratios),
                reference_units_per_geodesic_metre=distribution(ratios),
                skipped=dict(skipped),official_distance_unit_confirmed=False,
                warning='Reference units divided by straight-line metres between successive matched stations in node order. Curves, route changes and reference geometry can cause outliers. This is scale evidence, not a declaration of official units.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operations',required=True)
    parser.add_argument('--nodes',required=True)
    parser.add_argument('--stations',required=True)
    parser.add_argument('--route-audit',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    audit=json.loads(Path(args.route_audit).read_text(encoding='utf-8'))
    eligible={r['route_id'] for r in audit['routes'] if r['master_found'] and
              r['master_name']==r['candidate_name'] and r['route_type'] in ['3','4']}
    nodes=read_csv(args.nodes)
    with Path(args.operations).open(encoding='utf-8-sig',newline='') as stream:
        result=audit_reference(csv.DictReader(stream),nodes,eligible)
    result['coordinate_scale_check']=coordinate_check(nodes,read_csv(args.stations),eligible)
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['by_route','warning']},ensure_ascii=True))
