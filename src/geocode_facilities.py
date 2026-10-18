"""Prepare unreviewed facility coordinate candidates using a separate Kakao key."""
import argparse
import csv
import hashlib
import json
import math
import os
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path


ENDPOINT='https://dapi.kakao.com/v2/local/search/address.json'


class GeocodeSetupError(ValueError):
    """Fixed local configuration messages that contain no credentials."""


def parse_candidate(payload,district):
    if not isinstance(payload,dict) or not isinstance(payload.get('documents'),list):
        raise ValueError('Unexpected geocoding response')
    documents=payload['documents']
    result=dict(longitude=None,latitude=None,matched_address='',review_status='no_result')
    if not documents:
        return result
    if len(documents)!=1 or payload.get('meta',{}).get('total_count',len(documents))!=1:
        return dict(result,review_status='ambiguous')
    item=documents[0]
    address=item.get('road_address') or item.get('address') or {}
    if address.get('region_1depth_name') not in ['서울','서울특별시']:
        return dict(result,review_status='outside_seoul_or_unknown')
    if address.get('region_2depth_name')!=district:
        return dict(result,review_status='district_mismatch')
    try:
        x,y=float(item['x']),float(item['y'])
        if not (math.isfinite(x) and math.isfinite(y) and 124<=x<=132 and 33<=y<=40):
            raise ValueError('Invalid coordinates')
    except (ValueError,TypeError,KeyError):
        return dict(result,review_status='invalid_coordinates')
    return dict(result,longitude=x,latitude=y,
                matched_address=address.get('address_name',''),review_status='candidate_unreviewed')


def require_kakao_key(settings):
    key=settings.get('KAKAO_REST_API_KEY','').strip()
    if not key or key.startswith('YOUR_'):
        raise GeocodeSetupError('Set KAKAO_REST_API_KEY in local .env; the bus API key is not used')
    return key


def load_key(path):
    settings={}
    if Path(path).exists():
        for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                name,value=line.split('=',1)
                settings[name.strip()]=value.strip().strip('\"').strip("'")
    if os.environ.get('KAKAO_REST_API_KEY'):
        settings['KAKAO_REST_API_KEY']=os.environ['KAKAO_REST_API_KEY']
    return require_kakao_key(settings)


def collect(source,output,cache_dir,settings='.env',limit=5):
    key=load_key(settings)
    if not 1<=limit<=300:
        raise GeocodeSetupError('Use a request limit between 1 and 300')
    target=Path(output)
    if target.exists():
        raise GeocodeSetupError('Output exists; choose a new file to preserve manual reviews')
    cache=Path(cache_dir)
    cache.mkdir(parents=True,exist_ok=True)
    with Path(source).open(encoding='cp949',newline='') as stream:
        facilities=list(csv.DictReader(stream))
    calls=0
    results=[]
    for row in facilities:
        address=row['시설주소'].strip()
        result=dict(facility_id=row['시설코드'],name=row['시설명'],district=row['시군구명'],
                    address=address,longitude=None,latitude=None,matched_address='',
                    coordinate_source=ENDPOINT,review_status='pending_request_limit')
        path=cache/(hashlib.sha256(address.encode()).hexdigest()+'.json')
        try:
            if path.exists():
                payload=json.loads(path.read_text(encoding='utf-8'))['response']
            elif calls<limit:
                calls+=1
                query=urllib.parse.urlencode({'query':address,'analyze_type':'exact','size':10})
                request=urllib.request.Request(ENDPOINT+'?'+query,headers={'Authorization':'KakaoAK '+key})
                try:
                    with urllib.request.urlopen(request,timeout=20) as response:
                        raw=response.read(2_000_000)
                finally:
                    time.sleep(.25)
                if key.encode() in raw:
                    raise ValueError('Response unexpectedly contains credential')
                payload=json.loads(raw)
                parse_candidate(payload,row['시군구명'])
                path.write_text(json.dumps(dict(query=address,source=ENDPOINT,
                                fetched_at_utc=datetime.now(timezone.utc).isoformat(),response=payload),
                                ensure_ascii=False,indent=2),encoding='utf-8')
            else:
                results.append(result)
                continue
            result.update(parse_candidate(payload,row['시군구명']))
        except Exception as error:
            result['review_status']='request_error_'+type(error).__name__
        results.append(result)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['facility_id','name','district','address','longitude',
                             'latitude','matched_address','coordinate_source','review_status'])
        writer.writeheader();writer.writerows(results)
    summary=dict(requests=calls,facilities=len(results),statuses=dict(Counter(r['review_status'] for r in results)))
    print(json.dumps(summary))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default='data/raw/seoul_disability_facilities.csv')
    parser.add_argument('--output',required=True)
    parser.add_argument('--cache-dir',default='data/raw/geocoding_cache')
    parser.add_argument('--settings',default='.env')
    parser.add_argument('--limit',type=int,default=5)
    args=parser.parse_args()
    try:
        collect(args.source,args.output,args.cache_dir,args.settings,args.limit)
    except Exception as error:
        if isinstance(error,GeocodeSetupError):
            print(str(error))
        else:
            print('Geocoding failed ('+type(error).__name__+')')
        raise SystemExit(1)
