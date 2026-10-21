# 서울 버스의 전기저상 전환 검토

노선별 저상차량 구성과 운영 제약을 분석하고, 관련 시설 연결을 고려해 전기저상 전환의 검토 대상을 제안한다. 간선·지선 후보 375개 노선의 2026-10-13~15 운행기록 112,864행을 사용했다.

## 주요 결과

- 미확인 차량을 고려해도 일부 노선의 저상 구성 차이가 남는다. 미확인을 일반버스로 채우지 않고 하한·상한으로 제시한다.
- 저상 기록 비중 상한이 30% 미만이며 확보한 예외승인표와 연결되지 않은 후보는 6개다. 공식 예외 사유가 없다는 사실이 즉시 교체 가능함을 보장하지 않는다.
- **172번**은 후보 중 500m 연결 시설이 15곳으로 가장 많고, 일반 확인 차량은 20대다. 시설 연결 범위와 비저상 대체 가능성을 검토할 사례다.
- **1137번**은 500m 연결 시설 9곳 중 2곳에서 다른 노선의 저상 비중이 50% 기준을 충족하는지 불확실하다. 실제 목적지·방향과 차량 분류를 확인할 사례다.
- 반경을 800m로 넓히면 시설 연결 순서와 다른 노선 진단이 달라진다. 확정 교체 순위로 제시하지 않는다.

[공개 보고서](output/pdf/analysis_review_draft.pdf) · [후보별 시설 비교](docs/candidate-facility-comparison.md) · [검토 유형·기준 민감도](docs/route-review-types.md)

![운행기록 구성](outputs/public/figures/supply_record_composition.png)

시설 수는 통행 수요·휠체어 이용자 수가 아니다. 주변 노선은 실제 목적지와 방향이 같은 대체 교통편으로 검증되지 않았다. 탄소감축량·실측 대기시간·접근성 개선 효과는 산출하지 않았다. [전체 범위와 한계](docs/scope-decision.md).

## 실행

Python 3.12 기준이다. 수집·집계·검사는 표준 라이브러리로 실행한다. 그림은 `requirements.txt`, PDF는 `requirements-report.txt`의 추가 패키지가 필요하다.

```powershell
python -m unittest discover -s tests
python -m src.review_types --output data/processed/route_review_check.json
```

공개 집계를 사용한 두 번째 명령은 별도 원자료나 API 키가 필요 없다. 출력 폴더가 없으면 먼저 준비한다. 시설 연결 재계산과 원자료부터의 전체 실행은 [재현 순서](docs/reproduce.md)를 따른다.

```powershell
python -m pip install -r requirements-report.txt
python scripts/build_review_pdf.py --output data/processed/report_check.pdf
```

보고서는 당시 분석 결과를 설명하는 고정 원고다. 입력 결과를 바꾸면 수치·해석과 그림도 함께 검토해야 한다. 현재 API 재호출로 2026-10-17 분류 스냅샷을 그대로 재현할 수는 없다.

## 구성

| 경로 | 역할 |
|---|---|
| `src/` | API 수집, 원자료 검사, 노선·시설 분석, 그림 생성 |
| `src/route_records.py` | 일별 기록 검증과 노선 합산의 공통 구현 |
| `scripts/build_review_pdf.py` | 페이지 그리기와 보고서 내용 조립 |
| `tests/` | 중복·분모·미확인 분류·주소·후보 비교 검사 |
| `configs/` | 후보 노선, 공식 예외승인 사실표, 위치 시나리오 |
| `outputs/public/` | 공개 가능한 집계와 결과 그림 |
| `docs/` | 방법·해석·재현 안내, 검증 근거가 담긴 연구 기록 |

자료의 출처·이용조건은 [데이터 안내](data/README.md), 확보 당시 크기·해시는 `data/manifest.json`에 있다. 원자료·행 단위 가공자료·인증키·개인 신청서는 Git에서 제외한다. API를 새로 수집할 때만 `.env.example`을 참고해 로컬 인증키를 설정한다.

심사용 코드는 [분석 브랜치](https://github.com/daara0322/TransportationData/tree/codex/supply-analysis)를 사용한다. 공개 보고서는 개인정보가 없는 작업본이며, 개인 제출 파일과 발송 여부는 이 저장소에서 관리하지 않는다. AI 서비스·활용 범위·주요 요청 요약은 보고서에 기재했다. [공모전 제출 요건](docs/submission-requirements.md).
