"""Collect public positions without logging credentials or request URLs."""
import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


def parse_positions(payload, route_id):
    root = ET.fromstring(payload)
    code = root.findtext('./msgHeader/headerCd')
    if code is None:
        raise ValueError('API response has no header code')
    if code == '4':
        return []
    if code != '0':
        raise ValueError('API header code: ' + code)
    result = []
    for item in root.findall('./msgBody/itemList'):
        vehicle_id = item.findtext('vehId', '').strip()
        if not vehicle_id:
            raise ValueError('Vehicle identifier missing')
        bus_type = item.findtext('busType', '').strip()
        result.append(dict(route_id=route_id, vehicle_id=vehicle_id,
                           bus_type=bus_type, low_floor={'0': False, '1': True}.get(bus_type),
                           provider_time=item.findtext('dataTm'),
                           section_order=item.findtext('sectOrd'),
                           is_running=item.findtext('isrunyn')))
    return result


def safe_error_message(error):
    return 'Request failed (' + type(error).__name__ + ')'


def load_settings(path='.env'):
    values = {}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()
    key = os.environ.get('SEOUL_BUS_API_KEY') or values.get('SEOUL_BUS_API_KEY')
    base = values.get('SEOUL_BUS_API_BASE_URL', 'http://ws.bus.go.kr/api/rest/buspos')
    parsed = urllib.parse.urlparse(base)
    if not key or parsed.hostname != 'ws.bus.go.kr' or parsed.path != '/api/rest/buspos':
        raise ValueError('Missing credential or unexpected official API destination')
    if parsed.scheme not in ['http', 'https'] or parsed.query or parsed.fragment or parsed.username:
        raise ValueError('Unexpected API configuration')
    return key, base


def collect(route_ids, output_dir, settings='.env'):
    if not route_ids or len(route_ids) > 40 or len(set(route_ids)) != len(route_ids):
        raise ValueError('Use 1 to 40 distinct routes per invocation')
    if any(not re.fullmatch(r'\d{9}', value) for value in route_ids):
        raise ValueError('Invalid route identifier')
    key, base = load_settings(settings)
    now = datetime.now(timezone.utc)
    folder = Path(output_dir) / now.strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True, exist_ok=False)
    records, statuses = [], []
    for route in route_ids:
        try:
            query = urllib.parse.urlencode({'serviceKey': key, 'busRouteId': route})
            request = urllib.request.Request(base + '/getBusPosByRtid?' + query,
                                             headers={'User-Agent': 'TransportationDataResearch/0.1'})
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = response.read(4_000_000)
            if key.encode() in payload:
                raise ValueError('Response unexpectedly contains credential')
            items = parse_positions(payload, route)
            (folder / (route + '.xml')).write_bytes(payload)
            stamp = datetime.now(timezone.utc).isoformat()
            records.extend(dict(item, collected_at_utc=stamp) for item in items)
            statuses.append(dict(route_id=route, status='ok' if items else 'no_data', count=len(items)))
        except Exception as error:
            statuses.append(dict(route_id=route, status='error', error=safe_error_message(error)))
        time.sleep(0.15)
    result = dict(started_at_utc=now.isoformat(), requests=len(route_ids), statuses=statuses, records=records)
    (folder / 'snapshot.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'snapshot': str(folder / 'snapshot.json'), 'requests': len(route_ids),
                      'records': len(records), 'failures': sum(s['status']=='error' for s in statuses)}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--routes-file', required=True, help='JSON list of route IDs')
    parser.add_argument('--output-dir', default='data/raw/bus_positions')
    args = parser.parse_args()
    try:
        collect(json.loads(Path(args.routes_file).read_text(encoding='utf-8-sig')), args.output_dir)
    except Exception as error:
        print(safe_error_message(error))
        raise SystemExit(1)
