"""Read-only quality audit; source distances are not assumed to be kilometres."""
import argparse
import csv
import json
import math
from collections import Counter
from contextlib import nullcontext
from pathlib import Path


def clean(value):
    return (value or '').replace('\ufeff', '').strip()


def audit_operations(source):
    context = (Path(source).open(encoding='utf-8-sig', newline='')
               if isinstance(source, (str, Path)) else nullcontext(source))
    dates, routes, vehicles, missing = Counter(), Counter(), set(), Counter()
    seen = set()
    count = duplicates = 0
    distance = dict(positive_rows=0, zero_rows=0, negative_rows=0,
                    missing_rows=0, invalid_rows=0,
                    positive_sum_source_units=0.0, unit_status='unverified')
    with context as stream:
        reader = csv.DictReader(stream)
        reader.fieldnames = [clean(x) for x in (reader.fieldnames or [])]
        required = ['기준일', '운행순번', '버스ID', '노선ID', '운행거리', 'SSTTN_DT']
        absent = sorted(set(required) - set(reader.fieldnames))
        if absent:
            raise ValueError('Missing required columns: ' + ', '.join(absent))
        columns = reader.fieldnames
        for raw in reader:
            row = {k: clean(v) for k, v in raw.items() if k is not None}
            count += 1
            for key in columns:
                if not row.get(key):
                    missing[key] += 1
            dates[row['기준일']] += 1
            routes[row['노선ID']] += 1
            if row['버스ID']:
                vehicles.add(row['버스ID'])
            key = tuple(row[x] for x in ['기준일', '노선ID', '버스ID', '운행순번', 'SSTTN_DT'])
            if key in seen:
                duplicates += 1
            seen.add(key)
            value = row['운행거리']
            if not value:
                distance['missing_rows'] += 1
                continue
            try:
                number = float(value)
            except ValueError:
                distance['invalid_rows'] += 1
                continue
            if not math.isfinite(number):
                distance['invalid_rows'] += 1
            elif number < 0:
                distance['negative_rows'] += 1
            elif number == 0:
                distance['zero_rows'] += 1
            else:
                distance['positive_rows'] += 1
                distance['positive_sum_source_units'] += number
    return dict(row_count=count, column_count=len(columns), columns=columns,
                dates=dict(sorted(dates.items())), vehicle_count=len(vehicles),
                route_count=len(routes), missing_counts=dict(missing),
                duplicate_candidate_rows=duplicates, distance=distance)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit_operations(args.source)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ['columns', 'missing_counts']}, ensure_ascii=True))
