"""Review actions from pooled route records; thresholds are exploratory, not policy."""
import argparse
from collections import Counter
import json
from pathlib import Path

from src.route_records import COUNTS, aggregate_routes

THRESHOLDS = (30, 50, 80)


def classify(low, unknown, total, threshold, exempt=False):
    if total <= 0 or min(low, unknown) < 0 or low + unknown > total or not 0 < threshold <= 100:
        raise ValueError('Invalid counts or percentage threshold')
    if 100 * (low + unknown) < threshold * total:
        return 'operational_constraint' if exempt else 'low_composition'
    if 100 * low >= threshold * total:
        return 'lower_meets'
    return 'information_needed'


def analyse(source, exemptions):
    constraints = {r['route_id']: r['primary_constraint'] for r in exemptions['matched_routes']}
    pooled = aggregate_routes(source['by_route_day'])
    routes = []
    for route_id, values in sorted(pooled.items()):
        row = {'route_id': route_id, 'route_name': values['route_name'],
               **{key: values[key] for key in COUNTS}}
        n, low, regular, unknown = (row[k] for k in COUNTS)
        reason = constraints.get(row['route_id'])
        types = {str(t): classify(low, unknown, n, t, reason is not None) for t in THRESHOLDS}
        routes.append({**row, 'lower_bound': low/n, 'upper_bound': (low+unknown)/n,
                       'official_exception_reason': reason, 'review_type_by_threshold': types})
    names = ['low_composition', 'operational_constraint', 'information_needed', 'lower_meets']
    thresholds = []
    for t in THRESHOLDS:
        counts = Counter(r['review_type_by_threshold'][str(t)] for r in routes)
        thresholds.append({'percent': t, 'counts': {name: counts[name] for name in names}})
    low_types = {'low_composition', 'operational_constraint'}
    stable = [r['route_name'] for r in routes if all(v in low_types for v in r['review_type_by_threshold'].values())]
    changed = sum(len(set(r['review_type_by_threshold'].values())) > 1 for r in routes)
    return {'route_count': len(routes), 'unit': 'pooled operation records, not vehicles or station arrivals',
            'thresholds': thresholds, 'stable_low_below_30': stable,
            'threshold_sensitive_routes': changed, 'routes': routes,
            'warning': 'Exploratory thresholds, conditional historical classification; not replacement priority or measured accessibility. Exception absence does not prove feasibility. Location review remains a separate facility-level flag.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supply', default='outputs/public/supply_records.json')
    parser.add_argument('--exceptions', default='outputs/public/exemption_crosscheck.json')
    parser.add_argument('--output', default='outputs/public/route_review_types.json')
    args = parser.parse_args()
    source = json.loads(Path(args.supply).read_text(encoding='utf-8'))
    exemptions = json.loads(Path(args.exceptions).read_text(encoding='utf-8'))
    result = analyse(source, exemptions)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'routes'}, ensure_ascii=False))
