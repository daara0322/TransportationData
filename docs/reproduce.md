# 분석 재현 순서

Python 3.12에서 확인했다. 수집·집계·테스트는 표준 라이브러리로 실행하고, 그림만 `requirements.txt`의 matplotlib를 사용한다. 한글 그림에는 맑은 고딕 또는 Noto Sans CJK KR 등 한글 글꼴이 필요하다.

## 원자료 준비

`data/README.md`의 공식 링크에서 파일을 내려받아 명시된 이름으로 `data/raw/`에 둔다. 확보 당시 파일의 크기·해시는 `data/manifest.json`과 대조한다. 제공기관의 파일이 바뀌면 예전 해시와 결과가 달라질 수 있으므로 새 수집일과 해시를 기록한다.

실시간 API 원본은 2026-10-17 당시 스냅샷이며 Git에 없다. 지금 재호출하면 동일 표본이 되지 않는다. 당시 분류를 그대로 재현하려면 팀이 보관한 스냅샷이 필요하다. 공개 저장소의 노선별 결과는 확인할 수 있지만 그 집계만으로 차량 단위 분류를 복원할 수는 없다.

시설 CSV는 CP949, T-Data CSV는 셀 내부 BOM을 포함한 UTF-8이다. 원본을 덮어쓰지 않는다. 배차 차량 이력에는 운전자 ID 열이 있어 원본·행 단위 자료를 공개 결과에 포함하지 않는다.

## 실행

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.audit_operations data/raw/tdata_vehicle_operations.csv --output outputs/public/operations_audit.json
python -m src.link_positions --operations data/raw/tdata_vehicle_operations.csv --snapshot data/raw/bus_positions/authorization_snapshot.json --output outputs/public/lowfloor_linkage_authorization.json
python -m src.audit_route_master --master data/raw/tdata_route_master.csv --vehicle-routes data/raw/tdata_vehicle_routes.csv --candidates outputs/public/authorization_route_candidates.json --linkage outputs/public/lowfloor_linkage_authorization.json --snapshot data/raw/bus_positions/authorization_snapshot.json --output outputs/public/route_master_audit.json
python -m src.supply_records --operations data/raw/tdata_vehicle_operations.csv --snapshot data/raw/bus_positions/authorization_snapshot.json --route-audit outputs/public/route_master_audit.json --output outputs/public/supply_records.json
python -m src.audit_dispatch --stations data/raw/tdata_station_dispatch_history.csv --vehicles data/raw/tdata_vehicle_dispatch_history.csv --output outputs/public/dispatch_history_audit.json
python -m src.prepare_spatial --nodes data/raw/tdata_route_nodes.csv --stations data/raw/tdata_stations.csv --route-audit outputs/public/route_master_audit.json --edges-output data/processed/route_station_edges.csv --audit-output outputs/public/spatial_preparation_audit.json
python -m src.figures
```

시설 좌표나 연료를 추정으로 채우는 처리는 포함하지 않는다.

## 검산

- 운행통계 원본 전체는 291,637행, 현재 현황 범위는 375개 후보의 112,864행이다.
- 현황의 저상 확인·일반 확인·미확인 기록 합계는 112,864행이어야 한다.
- 날짜별·유형별 집계의 합은 전체 현황 합과 같아야 한다.
- 미확인 기록이 있는 결과에는 비율의 범위가 남아야 한다.
- 가상·중복 정류장을 제외한 생활권 입력은 노선·정류장 연결 27,823개다.
- 배차 이력 검사 결과가 실제시각을 검증했다고 표시해서는 안 된다.
- `.env`, 원본, 행 단위 가공 자료와 설치 도구는 Git 제외 대상이다.

## 거리 참조 대조

```powershell
python -m src.distance_reference --operations data/raw/tdata_vehicle_operations.csv --nodes data/raw/tdata_route_nodes.csv --stations data/raw/tdata_stations.csv --route-audit outputs/public/route_master_audit.json --output outputs/public/distance_reference_audit.json
```

시설 좌표 수집은 별도 키와 건물 위치 검수가 필요하다. 절차와 해석 한계는 `research/2026-10-18-distance-and-geocoding.md`에 기록했다. 아직 실제 지오코딩 요청을 검증한 단계는 아니다.

## 시설 후보의 주소·거리 진단

전체 주소 검색 결과가 로컬에 있을 때 실행한다. 새 `--details-output` 이름을 사용해야 하며 기존 수동 검토 파일을 덮어쓰지 않는다.

```powershell
python -m src.facility_catchments --facilities data/processed/facility_geocode_candidates_full.csv --edges data/processed/route_station_edges.csv --output outputs/public/facility_catchment_initial_diagnostic.json --details-output data/processed/facility_address_review_v2.csv
```

이는 미검수 좌표의 진단이다. 완전한 도로명·건물번호 문자열 일치도 건물 위치 확인으로 취급하지 않는다. 결과의 분모와 해석은 `research/2026-10-18-facility-catchments.md`를 참고한다.

미검색 시설의 상세 표기 분리 재조회와 최신 진단은 다음 순서다. `work-dir`와 출력 파일은 존재하지 않는 새 경로여야 한다. 재조회에는 로컬 카카오 키와 네트워크가 필요하며 응답은 주소별 캐시를 재사용한다. 원본 시설 주소는 바꾸지 않는다.

```powershell
python -m src.retry_facility_addresses --input data/processed/facility_geocode_candidates_full.csv --work-dir data/processed/geocode_retry_building --output data/processed/facility_geocode_candidates_refined.csv --limit 30
python -m src.facility_catchments --facilities data/processed/facility_geocode_candidates_refined.csv --edges data/processed/route_station_edges.csv --output outputs/public/facility_catchment_diagnostic.json --details-output data/processed/facility_address_review_refined.csv
```

층·호수 등 단지 내부 상세 정보가 검색 쿼리에서 빠질 수 있으므로 재조회 응답도 실제 건물 위치의 확정값이 아니다.

## 시설 주변 노선의 전체 기록 구성

```powershell
python -m src.facility_supply --facilities data/processed/facility_geocode_candidates_refined.csv --edges data/processed/route_station_edges.csv --supply outputs/public/supply_records.json --output outputs/public/facility_supply_diagnostic.json --details-output data/processed/facility_supply_review.csv
python -m src.facility_supply_figure
```

시설별 출력은 새 경로만 허용하며 입력·출력 경로가 서로 같으면 중단한다. 이 분석은 노선 전체의 기록 구성을 연결한 사전 진단이고 정류장 단위 실측 도착비율이 아니다. 해석은 `research/2026-10-18-facility-supply.md`를 참고한다.

## 시설 종류별 연결 범위 점검

```powershell
python -m src.facility_types --master data/raw/seoul_disability_facilities.csv --details data/processed/facility_supply_review.csv --output outputs/public/facility_type_audit.json
```

원본 CP949 시설 CSV에서 종류별 전체 수를 유지하고 주소 일치 후보의 연결 범위와 기존 50% 진단을 나눈다. 시설 종류를 휠체어 수요 가중치로 사용하지 않는다.

## 같은 시설의 두 주소 대표점 비교

아래 준비 코드는 공개 시나리오 설정을 카카오 수집기가 읽는 CP949 CSV로 만든다. 기존 파일이 있으면 새 작업 경로를 사용한다. 실제 조회에는 로컬 키·네트워크가 필요하며 응답은 캐시된다.

```python
import csv, json
from pathlib import Path
config = json.loads(Path('configs/gangbuk_building_scenarios.json').read_text(encoding='utf-8'))
with Path('data/processed/gangbuk_building_queries.csv').open('x', encoding='cp949', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(config['scenarios'][0]))
    writer.writeheader()
    writer.writerows(config['scenarios'])
```

```powershell
python -m src.geocode_facilities --source data/processed/gangbuk_building_queries.csv --output data/processed/gangbuk_building_candidates.csv --limit 2
python -m src.building_sensitivity --reference-id C5044 --candidates data/processed/gangbuk_building_candidates.csv --edges data/processed/route_station_edges.csv --supply outputs/public/supply_records.json --output outputs/public/gangbuk_building_sensitivity.json
```

이는 시설 1곳의 위치 시나리오 2개다. 원래 시설 전체 집계의 입력으로 합치지 않는다. 별관 주소의 실제 출입구 확인과 보행 동선 검수는 미완료다.

그림은 `python -m src.building_sensitivity_figure`로 공개 비교 JSON에서 재생성한다. 필요한 matplotlib와 한글 글꼴은 위 그림 실행 조건과 동일하다.

## 검토용 PDF

```powershell
python -m pip install -r requirements-report.txt
python scripts/build_review_pdf.py
```

기본 출력은 `output/pdf/analysis_review_draft.pdf`이며 표지·본문 5쪽·참고자료를 합쳐 총 7쪽이다. Windows 맑은 고딕 경로를 기본으로 사용하며 다른 환경에서는 한글 TrueType 글꼴을 `--font`와 `--bold-font`로 지정한다. 이미 생성한 공개 집계 JSON·그림이 필요하다. 이는 특정 시점 결과를 설명하는 검토용 원고이므로 입력이 바뀌면 문장과 표도 함께 검토해야 한다. 최종 제출 파일로 자동 전환하거나 참가신청서를 작성하지 않는다.

개인 확인본을 만들 때는 로컬 JSON의 `name`, `affiliation`, `motivation`을 사용한다. 개인정보가 있는 출력은 Git 제외 경로만 허용한다.

```powershell
python scripts/build_review_pdf.py --profile data/processed/submission/profile.json --output data/processed/submission/이름_분석보고서.pdf
```

원본 신청서는 별도 동의·서명 작성이 필요하며 이 명령이 신청서 작성이나 메일 발송을 대신하지 않는다.
