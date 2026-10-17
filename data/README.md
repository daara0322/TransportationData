# 원자료 기록

확보일: 2026-10-17 (한국시간). 해시와 크기는 `manifest.json` 참고.

| 로컬 파일 | 원문 페이지 | 다운로드 주소 | 범위와 제한 |
|---|---|---|---|
| raw/tdata_vehicle_operations.csv | https://t-data.seoul.go.kr/dataprovide/trafficdataviewfile.do?data_id=84 | https://t-data.seoul.go.kr/dataprovide/download.do?id=10277 | 원본에서 확인한 기준일 2026-10-13~15. 서울 외 지역 포함. 거리 단위 미확인 |
| raw/seoul_bus_authorization_2026_01.xlsx | https://news.seoul.go.kr/traffic/archives/6838 | https://news.seoul.go.kr/traffic/files/2012/02/69ae225a251650.68990697.xlsx | 2026년 1월 인가현황. 차량별 연료·저상 여부와 ID 없음 |
| raw/seoul_lowfloor_exceptions_2026_03.png | https://news.seoul.go.kr/traffic/archives/513625 | https://news.seoul.go.kr/traffic/files/2025/01/6979ce7991a467.02151287.png | 2026년 예외노선표. 이미지 원본 보존 |
| raw/seoul_bus_status_2026_01.html | https://news.seoul.go.kr/traffic/archives/300 | 동일 | 총량 검산용 웹페이지 |
| raw/bus_positions/ | https://www.data.go.kr/data/15000332/openapi.do | http://ws.bus.go.kr/api/rest/buspos/getBusPosByRtid | 2026-10-17 실시간 응답. 키와 쿼리 URL은 보관하지 않음. fuel 정보 없음 |
| raw/tdata_route_master.csv | https://t-data.seoul.go.kr/dataprovide/trafficdataviewfile.do?data_id=53 | https://t-data.seoul.go.kr/dataprovide/download.do?id=10246 | 1,751행. 유형·지역코드·기종점·거리 등. 차량별 연료 없음 |
| raw/tdata_vehicle_routes.csv | https://t-data.seoul.go.kr/dataprovide/trafficdataviewfile.do?data_id=60 | https://t-data.seoul.go.kr/dataprovide/download.do?id=10253 | 16,130행. 차량·노선·회사 ID. 시점 일치 검증 필요 |
| raw/tdata_route_details.csv | https://t-data.seoul.go.kr/dataprovide/trafficdataviewfile.do?data_id=54 | https://t-data.seoul.go.kr/dataprovide/download.do?id=10247 | 1,797행. 기종점·회차 정류장 ID와 순번. 후속 대조용 |

확대 수집의 합본은 `raw/bus_positions/authorization_snapshot.json`이다. 후보 393개 요청, 350개 차량 기록 있음, 43개 데이터 없음, 요청 오류 0개다. 40개 이하 묶음별 원본 XML과 스냅샷은 `raw/bus_positions/census/`에 보존한다. 그전에 수집한 19개 목적표본은 확대 수집과 별개이며 두 표본을 중복 합산하지 않는다. 원본 응답에는 차량 식별·위치가 있으므로 공개 결과는 노선별 집계만 사용한다.

T-Data는 출처표시 조건을 안내한다. 서울시 페이지는 공공누리 4유형을 안내하므로 첨부파일의 별도 조건도 확인해야 한다. 현재 원본과 가공 개인·차량 단위 자료는 재배포하지 않는다. 출처를 인용해 분석 사실을 보고하고 원본 다운로드 경로를 제공한다.

거리 컬럼에는 셀 내부 BOM(U+FEFF)이 포함돼 있어 읽기 단계에서 제거한다. 원본 자체를 덮어쓰지 않는다. 버스 ID·노선 ID는 문자열로 보존한다. 거리 합계는 단위가 확인될 때까지 source units로 기록한다.
