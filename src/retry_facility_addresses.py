"""Retry no-result facility addresses using conservative building-only queries."""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from src.facility_catchments import ROAD_BUILDING
from src.geocode_facilities import collect


def building_query(address):
    split=re.search(r'[,()]',address)
    if split is None:
        return None
    query=address[:split.start()].strip()
    match=ROAD_BUILDING.search(query)
    if match is None or match.end()!=len(query):
        return None
    if split.group()==',':
        suffix=address[split.end():].strip()
        if not re.match(r'(?:지하?|지상)?\s*\d',suffix):
            return None
    return query


def merge_retry(original,retries):
    indexed={row['facility_id']:row for row in original}
    if len(indexed)!=len(original):
        raise ValueError('Duplicate original facility ID')
    updates={}
    fields=['longitude','latitude','matched_address','coordinate_source','review_status']
    for retry in retries:
        identifier=retry['facility_id']
        row=indexed.get(identifier)
        if row is None or identifier in updates or row['review_status']!='no_result':
            raise ValueError('Retry must target one previously unmatched facility')
        if building_query(row['address'])!=retry['address']:
            raise ValueError('Retry query does not match the original building address')
        updates[identifier]=dict(row,**{k:retry[k] for k in fields if k in retry},
                                 query_address=retry['address'],query_method='building_detail_removed')
    return [updates.get(row['facility_id'],dict(row)) for row in original]


def read(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))


def write(path,rows,encoding='utf-8-sig'):
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding=encoding,newline='') as stream:
        fields=list(dict.fromkeys(key for row in rows for key in row))
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader();writer.writerows(rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True)
    parser.add_argument('--work-dir',required=True,help='New private directory for retry input and responses')
    parser.add_argument('--output',required=True)
    parser.add_argument('--limit',type=int,default=5)
    args=parser.parse_args()
    original=read(args.input)
    if Path(args.output).exists() or Path(args.work_dir).exists():
        raise ValueError('Use new output paths to preserve previous reviews')
    prepared=[]
    for row in original:
        query=building_query(row['address'])
        if row['review_status']=='no_result' and query:
            prepared.append({'시설코드':row['facility_id'],'시설명':row['name'],
                             '시군구명':row['district'],'시설주소':query})
    if not prepared:
        raise ValueError('No conservative building-address retries available')
    work=Path(args.work_dir)
    source=work/'retry_queries.csv';response=work/'retry_responses.csv'
    write(source,prepared,'cp949')
    collect(source,response,'data/raw/geocoding_cache',limit=args.limit)
    retries=[row for row in read(response) if row['review_status']!='pending_request_limit']
    merged=merge_retry(original,retries)
    write(args.output,merged)
    print(json.dumps(dict(retry_facilities=len(retries),source_facilities=len(merged),
                         statuses=dict(Counter(row['review_status'] for row in merged)))))
