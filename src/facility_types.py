"""Audit facility-type coverage without inferring wheelchair travel demand."""
import argparse
import csv
import json
import math
from pathlib import Path

from src.facility_catchments import RADII


def audit_types(master,details):
    indexed={}
    groups={}
    for row in master:
        identifier=row['시설코드']
        kind=row['시설종류명(시설유형)']
        if not identifier or not kind or identifier in indexed:
            raise ValueError('Empty or duplicate facility identity/type')
        indexed[identifier]=kind
        group=groups.setdefault(kind,dict(facility_type=kind,source_facilities=0,linked_candidates=0,
                  by_radius=[dict(radius_metres=r,lower_bound_meets=0,upper_bound_below=0,
                                  uncertain=0,no_nearby_route=0) for r in RADII]))
        group['source_facilities']+=1
    seen=set()
    for row in details:
        required={'facility_id'}|{prefix+str(radius) for radius in RADII
                                 for prefix in ['best_route_share_lower_','best_route_share_upper_']}
        if not required.issubset(row):
            raise ValueError('Missing required facility composition columns')
        identifier=row['facility_id']
        if identifier not in indexed or identifier in seen:
            raise ValueError('Unknown or duplicate linked facility ID')
        seen.add(identifier)
        group=groups[indexed[identifier]]
        group['linked_candidates']+=1
        for item in group['by_radius']:
            tag=str(item['radius_metres'])
            lower=row['best_route_share_lower_'+tag]
            upper=row['best_route_share_upper_'+tag]
            if lower=='' and upper=='':
                item['no_nearby_route']+=1
                continue
            try:
                low,high=float(lower),float(upper)
                if not (math.isfinite(low) and math.isfinite(high) and 0<=low<=high<=1):
                    raise ValueError('Invalid interval')
            except (ValueError,TypeError):
                raise ValueError('Invalid conditional composition bounds') from None
            field='lower_bound_meets' if low>=.5 else 'upper_bound_below' if high<.5 else 'uncertain'
            item[field]+=1
    for group in groups.values():
        group['not_linked']=group['source_facilities']-group['linked_candidates']
    return dict(source_facilities=len(indexed),linked_candidates=len(seen),not_linked=len(indexed)-len(seen),
                diagnostic_threshold=.5,by_type=[groups[k] for k in sorted(groups)],
                warning='Facility types are retained as supplied, not wheelchair-user demand weights. The 50% threshold is diagnostic only. Linked facilities are unreviewed address-matching candidates. Missing coordinates stay in each source-type denominator. These whole-route composition categories do not verify local arrivals, walking access, travel demand or carbon reductions.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master',required=True)
    parser.add_argument('--details',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    paths=[Path(p).resolve() for p in [args.master,args.details,args.output]]
    if len(set(paths))!=len(paths):raise ValueError('Inputs and output must use distinct paths')
    with Path(args.master).open(encoding='cp949',newline='') as stream:master=list(csv.DictReader(stream))
    with Path(args.details).open(encoding='utf-8-sig',newline='') as stream:details=list(csv.DictReader(stream))
    result=audit_types(master,details)
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='by_type'},ensure_ascii=True))
