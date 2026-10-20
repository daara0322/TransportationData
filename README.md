# 버스 전환 우선순위 분석

탄소저감과 교통약자의 저상버스 이용 기회를 함께 고려해 차량 교체 후보를 비교하는 프로젝트다. 현재는 원자료 확보와 품질 확인 단계다. 저상 분류는 일부 연결했지만 차량별 연료와 거리 단위가 확인되지 않아 교체 순위나 탄소감축량은 산출하지 않았다.

## 확보한 자료

- 서울 T-Data 차량 운행통계 CSV: 2026-10-13~15, 291,637행, 42열.
- 서울시 2026년 1월 시내버스 인가현황 엑셀.
- 서울시 2026년 저상버스 예외승인 노선표 이미지.
- 서울 버스위치 API: 2026-10-17 오후, 인가현황과 이름을 대조한 후보 393개에 요청해 차량 위치 기록 4,433건 확보.
- T-Data 노선 마스터 1,751행, 차량별운행노선정보 16,130행, 노선 부가 정보 1,797행.

후보 노선의 과거 차량·노선 조합 7,251개 중 4,431개에 현재 저상 분류를 연결했다(61.1%). 서울 전체 보급률이 아니며, 미분류 2,820개를 일반버스로 취급하지 않는다. 현재 분류의 과거 시점 유효성도 추가 확인이 필요하다. 자세한 결과와 한계는 `docs/research/2026-10-17-lowfloor-linkage.md`에 적었다.

393개 후보 중 391개가 공식 노선 마스터에서 발견됐고, 이름이 다른 1개와 마스터에 없는 2개를 별도로 기록했다. 미확인 차량이 결과를 얼마나 바꿀 수 있는지 노선별 가능한 범위도 계산했다. 해석과 사례는 `docs/research/2026-10-17-route-master-validation.md`를 참고한다.

현황 분석은 ID·명칭과 유형을 확인한 간선·지선 후보 375개, 운행통계 112,864행으로 진행했다. 현재 분류를 연결한 저상 55,989행·일반 15,449행과 미확인 41,426행을 구분했다. 이 기록은 완주 운행 횟수나 승객 수로 확정하지 않았다.

정류장·경로와 시설 주소도 확보했다. 미검수 시설 좌표 후보를 이용한 거리·주변 노선 구성 사전 진단까지 진행했다. 실제 공간 수요 격차와 탄소 전환안은 아직 검증하지 않았다. 배차 이력은 시각의 규칙성이 높고 역전 기록이 있어 실제 관측인지 확인 전 대기시간 분석에 사용하지 않는다.

전체 상태는 [진행 체크리스트](docs/progress-checklist.md), 실행은 [재현 순서](docs/reproduce.md), 새 집계는 [진행 기록](docs/research/2026-10-17-supply-and-spatial-progress.md), 제출 조건은 [요건 확인](docs/submission-requirements.md)에 정리했다.

![운행기록 구성](outputs/public/figures/supply_record_composition.png)

운행통계에는 서울 외 지역 차량도 포함된다. 거리 단위와 비정상 기록을 확인하기 전에는 탄소계산에 사용하지 않는다. 공개 파일의 수정일을 장기 시계열 제공의 증거로 해석하지 않는다.

## 품질 점검 실행

Python 표준 라이브러리만 사용한다.

```powershell
python -m unittest discover -s tests -v
python -m src.audit_operations data/raw/tdata_vehicle_operations.csv --output outputs/public/operations_audit.json
python -m src.link_positions --operations data/raw/tdata_vehicle_operations.csv --snapshot data/raw/bus_positions/authorization_snapshot.json --output outputs/public/lowfloor_linkage_authorization.json
python -m src.audit_route_master --master data/raw/tdata_route_master.csv --vehicle-routes data/raw/tdata_vehicle_routes.csv --candidates outputs/public/authorization_route_candidates.json --linkage outputs/public/lowfloor_linkage_authorization.json --snapshot data/raw/bus_positions/authorization_snapshot.json --output outputs/public/route_master_audit.json
```

원본 경로와 출처는 `data/README.md`, 연구 진행상황은 `docs/research/2026-10-17-data-feasibility.md`에 기록했다. 저장소에는 코드·문서·노선별 집계 결과를 포함하고, 인증키와 원자료는 제외한다. 원자료는 출처에서 별도로 내려받아 `data/raw/`에 준비해야 한다.

API 수집에는 `.env.example`을 참고해 로컬 `.env`에 인증키를 설정한다. `.env`는 Git 제외 대상이다. `python -m src.bus_positions --routes-file configs/probe_routes.json`으로 최대 40개 노선을 수집한다. 매번 API 호출을 사용하며 응답 시점에 따라 결과가 달라진다. AI 활용 내역은 `docs/ai_usage.md`에 기록한다.

시설 주소 대조와 미검수 좌표의 정류장 거리 사전 진단: [진행 결과](docs/research/2026-10-18-facility-catchments.md). 좌표 후보는 확정 접근성이나 실제 이용 수요를 뜻하지 않는다.

시설 주변 노선의 저상 기록 구성은 [사전 진단](docs/research/2026-10-18-facility-supply.md)에 정리했다. 노선 전체 기록을 연결했으며 정류장 도착비율·대기시간·수요·탄소 효과는 미검증이다.

원래 탄소 비교의 미충족 입력과 시설 종류별 연결 범위는 [준비 상태 점검](docs/research/2026-10-18-readiness-and-facility-types.md)에 있다. [기관 문의 초안](docs/requests/bus-data-questions.md)은 팀 발송용이며 아직 보내지 않았다.

한 시설의 두 주소 후보가 약 42m 차이로 300m 진단을 바꾼 [위치 민감도 사례](docs/research/2026-10-19-building-location-sensitivity.md)도 확인했다. 원래 전체 집계와 별도이며 실제 접근성 격차로 확정하지 않았다.

검토용 PDF는 [보고서 작업본](output/pdf/analysis_review_draft.pdf), 최종 제출 전 부족 항목은 [제출 준비 대조표](docs/submission-gap-check.md)에 있다. 본문은 5쪽이지만 탄소 전환안은 미완료이며 최종 제출본이 아니다.

2026-10-20부터 1인 개인 참가로 진행한다. 현재 역할과 중복 작업을 줄이는 기준은 [작업 기준](docs/working-agreement.md)에 정리했다.
