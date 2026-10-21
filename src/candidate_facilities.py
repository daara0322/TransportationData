"""Compare candidate routes' facility connections and other-route composition."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path


RADII = (300, 500, 800)
THRESHOLDS = (.5, .8)


def compare(facilities, types, candidates, supply):
    seen = set()
    for f in facilities:
        key = f['facility_id']
        if not key or key in seen or key not in types:
            raise ValueError('Unknown, empty or duplicate facility identity')
        seen.add(key)
    if len({c['route_id'] for c in candidates}) != len(candidates):
        raise ValueError('Duplicate candidate identity')
    for r in supply.values():
        if not 0 <= r['lower'] <= r['upper'] <= 1:
            raise ValueError('Invalid route composition bounds')
    result = []
    for candidate in candidates:
        route_id = candidate['route_id']
        radii = []
        for radius in RADII:
            linked = []
            for f in facilities:
                nearby = {x for x in f['route_ids_'+str(radius)].split(';') if x}
                if route_id in nearby:
                    linked.append((f, nearby - {route_id}))
            checks = []
            for threshold in THRESHOLDS:
                counts = Counter()
                for _, others in linked:
                    # Unknown other routes have interval [0, 1]. The candidate is excluded.
                    lower = max((supply.get(i, {'lower': 0})['lower'] for i in others), default=0)
                    upper = max((supply.get(i, {'upper': 1})['upper'] for i in others), default=1)
                    category = ('no_other_route' if not others else 'lower_meets' if lower >= threshold
                                else 'all_upper_below' if upper < threshold else 'uncertain')
                    counts[category] += 1
                checks.append({'threshold': threshold, **{k: counts[k] for k in
                              ['lower_meets', 'all_upper_below', 'uncertain', 'no_other_route']}})
            radii.append({'radius_metres': radius, 'linked_facilities': len(linked),
                          'by_type': dict(sorted(Counter(types[f['facility_id']] for f, _ in linked).items())),
                          'facilities_with_missing_alternative_supply': sum(any(i not in supply for i in others) for _, others in linked),
                          'alternative_checks': checks})
        result.append({'route_id': route_id, 'route_name': candidate['route_name'], 'by_radius': radii})
    return {'reference_facilities': len(facilities), 'candidate_routes': len(result), 'routes': result,
            'warning': 'Counts are distinct facilities per route and overlap across routes. Candidate excluded from other-route checks. Whole-route record composition, not verified alternatives for a trip, demand, station arrivals or accessible walking paths. Address coordinates unreviewed. Thresholds are exploratory. Missing alternative supply uses [0,1]. No replacement ranking or carbon effect estimated.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--details', default='data/processed/facility_supply_review.csv')
    parser.add_argument('--master', default='data/raw/seoul_disability_facilities.csv')
    parser.add_argument('--review', default='outputs/public/route_review_types.json')
    parser.add_argument('--supply', default='outputs/public/facility_supply_diagnostic.json')
    parser.add_argument('--output', default='outputs/public/candidate_facility_comparison.json')
    args = parser.parse_args()
    read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
    with Path(args.details).open(encoding='utf-8-sig', newline='') as stream:
        facilities = list(csv.DictReader(stream))
    with Path(args.master).open(encoding='cp949', newline='') as stream:
        master = list(csv.DictReader(stream))
    types = {r['시설코드']: r['시설종류명(시설유형)'] for r in master}
    if len(types) != len(master):
        raise ValueError('Duplicate master facility identity')
    candidates = [r for r in read(args.review)['routes'] if r['review_type_by_threshold']['30'] == 'low_composition']
    supply = {r['route_id']: r for r in read(args.supply)['by_route']}
    result = compare(facilities, types, candidates, supply)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'reference_facilities': result['reference_facilities'], 'candidate_routes': result['candidate_routes']}))
