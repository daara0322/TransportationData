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
