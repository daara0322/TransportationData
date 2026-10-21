"""Build a clearly labelled seven-page review PDF: cover, five body pages, references."""
import argparse
import json
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph, Table, TableStyle


ROOT=Path(__file__).resolve().parents[1]
INK=colors.HexColor('#20333e')
TEAL=colors.HexColor('#177e8c')
MUTED=colors.HexColor('#566773')


def build(output,font_path,bold_path,profile_path=None):
    profile=json.loads(Path(profile_path).read_text(encoding='utf-8')) if profile_path else {}
    personal=bool(profile_path)
    if personal and not all(isinstance(profile.get(k),str) and profile[k].strip() for k in ['name','affiliation','motivation']):
        raise ValueError('A local profile requires name, affiliation and motivation')
    pdfmetrics.registerFont(TTFont('Korean',str(font_path)))
    pdfmetrics.registerFont(TTFont('KoreanBold',str(bold_path)))
    pdfmetrics.registerFontFamily('Korean',normal='Korean',bold='KoreanBold')
    styles={
        'body':ParagraphStyle('body',fontName='Korean',fontSize=9.4,leading=14.8,wordWrap='CJK',textColor=INK),
        'small':ParagraphStyle('small',fontName='Korean',fontSize=8,leading=11.8,wordWrap='CJK',textColor=MUTED),
        'cell':ParagraphStyle('cell',fontName='Korean',fontSize=7.8,leading=11,wordWrap='CJK',textColor=INK),
        'h':ParagraphStyle('h',fontName='KoreanBold',fontSize=17,leading=23,wordWrap='CJK',textColor=INK),
        'sub':ParagraphStyle('sub',fontName='KoreanBold',fontSize=10.8,leading=16,wordWrap='CJK',textColor=TEAL),
        'cover':ParagraphStyle('cover',fontName='KoreanBold',fontSize=25,leading=35,wordWrap='CJK',textColor=INK),
    }
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    if target.suffix.lower()!='.pdf':
        raise ValueError('Review output must use a .pdf extension')
    if personal and not target.resolve().is_relative_to((ROOT/'data/processed/submission').resolve()):
        raise ValueError('Personalized PDFs must stay in the Git-ignored submission directory')
    pdf=canvas.Canvas(str(target),pagesize=A4,pageCompression=1)
    pdf.setTitle('서울 버스의 전기저상 전환 검토 - 저상차량 구성과 운영 제약 분석')
    pdf.setAuthor(profile['name'] if personal else '검토용 초안 - 이름 미입력')
    width,height=A4
    left=46; usable=width-left*2;y=height-61
    def start(label):
        nonlocal y
        y=height-61
        pdf.setFillColor(MUTED);pdf.setFont('Korean',8)
        pdf.drawString(left,height-30,'TransportationData / '+('분석보고서' if personal else '검토용 초안')+' / 2026-10-21')
        pdf.setStrokeColor(colors.HexColor('#d8e1e6'));pdf.line(left,43,width-left,43)
        pdf.drawString(left,29,'저상차량 구성·운영 제약 분석')
        pdf.drawRightString(width-left,29,label)
    def draw(item,gap=9):
        nonlocal y
        w,h=item.wrap(usable,y-56)
        if y-h<56:raise ValueError('Page content exceeds bottom margin')
        item.drawOn(pdf,left,y-h);y-=h+gap
    def para(text,style='body',gap=9):draw(Paragraph(text,styles[style]),gap)
    def title(text):para(text,'h',13)
    def table(rows,widths):
        values=[[Paragraph(str(value),styles['cell']) for value in row] for row in rows]
        item=Table(values,colWidths=widths,hAlign='LEFT')
        item.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9f2f3')),
                                 ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),
                                 ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),
                                 ('BOTTOMPADDING',(0,0),(-1,-1),6),
                                 ('LINEBELOW',(0,0),(-1,0),.7,TEAL),
                                 ('LINEBELOW',(0,1),(-1,-1),.35,colors.HexColor('#dce3e7'))]))
        draw(item,10)
    def figure(name,maximum_height):
        item=Image(str(ROOT/'outputs/public/figures'/name))
        ratio=min(usable/item.imageWidth,maximum_height/item.imageHeight)
        item.drawWidth=item.imageWidth*ratio;item.drawHeight=item.imageHeight*ratio
        draw(item,8)
    def link(url,label=None):return '<a color="#177e8c" href="'+escape(url,quote=True)+'">'+escape(label or url)+'</a>'
    supply=json.loads((ROOT/'outputs/public/supply_records.json').read_text(encoding='utf-8'))
    facility=json.loads((ROOT/'outputs/public/facility_supply_diagnostic.json').read_text(encoding='utf-8'))
    location=json.loads((ROOT/'outputs/public/gangbuk_building_sensitivity.json').read_text(encoding='utf-8'))
    if (supply['eligible_routes']!=375 or supply['totals']['records']!=112864 or
        facility['source_facilities']!=274 or facility['address_matching_candidate_facilities']!=237 or
        location['reference_facilities']!=1 or location['coordinate_separation_metres']!=41.97):
        raise ValueError('Inputs changed: review the snapshot-specific narrative before rebuilding')
    start('표지')
    para('분석보고서' if personal else '검토용 보고서','sub',26)
    para('서울 버스의 전기저상 전환 검토를 위한<br/>저상차량 구성과 운영 제약 분석','cover',24)
    para('노선 구성 범위·시설 연계·공식 운영 제약의 교차 검토','sub',28)
    para('<b>이름 / 소속:</b> '+(escape(profile['name'])+' / '+escape(profile['affiliation']) if personal else '본인 직접 입력 필요'),gap=16)
    para('<b>문서 상태:</b> '+('개인 참가 분석보고서.' if personal else '개인 검토용 초안.')+' 현재 자료로 저상차량 구성 차이와 공식 운영 제약을 분석했다. 탄소감축량·최적 교체 순위·실제 접근성 효과의 산정은 연구 범위에서 제외했다.',gap=18)
    table([['확인한 분석','이번 분석에서 산출하지 않은 것'],
           ['375개 후보 노선의 112,864행 운행기록 구성<br/>시설 좌표 후보와 주변 노선의 조건부 연결<br/>대표 위치·반경 민감도','탄소감축량과 최적 교체 순위<br/>실제 통행 수요·출입구 접근성<br/>정류장 실측 도착 비율·대기시간']], [usable/2]*2)
    para('표지 + 본문 5쪽 + 참고자료 1쪽으로 구성했다. 인증키와 원본 행 단위 자료는 문서에 포함하지 않았다.','small')
    pdf.showPage()

    start('본문 1 / 5');title('1. 분석 배경·목적과 활용 데이터')
    para('전기저상 전환을 검토할 때 차량 도입 대수만으로 이용 기회와 운영 가능성을 판단하기 어렵다. 이번 분석은 미분류를 고려해도 남는 노선별 저상차량 구성 차이, 관련 시설 주변의 대상 노선 대안, 공식 예외승인 제약을 함께 살핀다. 탄소중립과의 연결은 전기저상 전환이라는 정책 대상에 두며 실제 탄소저감 효과를 검증한 연구로 제시하지 않는다.')
    para('<b>참여 동기:</b> '+(escape(profile['motivation']) if personal else '본인의 실제 참여 동기는 최종 원고에서 직접 작성해야 한다.')+' 기존 정책이 불공정하다는 결론은 전제하지 않았다.','small')
    sources=[
      ('차량 운행통계','서울시 BIS / T-Data','노선·차량·기록 연결, 10/13~15','https://t-data.seoul.go.kr/dataprovide/trafficdataviewfile.do?data_id=84'),
      ('버스위치정보 API','서울시 / 공공데이터포털','10/17 현재 저상 분류','https://www.data.go.kr/data/15000332/openapi.do'),
      ('노선·경유노드·정류장 자료','서울시 BIS / T-Data','ID 검증과 거리 연결; 개별 URL은 참고자료','https://t-data.seoul.go.kr/dataprovide/trafficdataviewfile.do?data_id=53'),
      ('인가현황·예외승인표','서울시 / 서울시 홈페이지','후보와 운영 제약 대조','https://news.seoul.go.kr/traffic/archives/513625'),
      ('장애인지역사회재활시설 목록','서울시 / 열린데이터광장','잠재 목적지의 주소; 실제 수요 아님','https://data.seoul.go.kr/dataList/OA-20429/A/1/datasetView.do'),
      ('주소 검색 API','카카오 / 카카오디벨로퍼스','주소의 좌표 후보; 건물·출입구 미검수','https://developers.kakao.com/docs/ko/kakaomap/common'),
    ]
    table([['자료·제공기관·플랫폼','선정 이유·URL']]+[
        [escape(name)+'<br/>'+escape(provider),escape(reason)+'<br/>'+link(url)] for name,provider,reason,url in sources], [175,usable-175])
    para('전체 운행통계는 291,637행이며, 마스터 ID·이름이 일치하고 간선·지선 유형인 375개 후보의 112,864행을 현황 범위로 사용했다. 서울 모든 버스 노선의 완전한 모집단은 아니다. 파일 기준일·수집일·해시는 저장소의 출처표와 manifest에 기록했다.','small')
    pdf.showPage()

    start('본문 2 / 5');title('2. 분석 과정·방법과 AI 활용')
    para('셀 내부 BOM·공백을 읽기 단계에서 처리하고 ID를 문자열로 보존했다. 현재 분류를 과거 기록에 붙일 때 노선 ID와 차량 ID를 함께 사용했다. 중복 후보키를 점검했고, 상충하거나 확인되지 않은 분류를 일반버스로 채우지 않았다.')
    para('노선의 저상 확인 기록 L, 일반 확인 R, 미분류 U를 먼저 합산하고 N=L+R+U에서 가능한 비중을 L/N ~ (L+U)/N으로 표시했다. 일별 비율의 단순 평균은 쓰지 않았다. 범위는 통계적 신뢰구간이 아니며 현재 분류의 과거 유효성을 전제로 한다.')
    para('시설은 300/500/800m 직선거리 내 정류장과 고유 노선에 연결했다. 같은 시설을 노선별·반경별로 중복 계산하지 않았다. 방향·목적지·보행 장애물과 부분 운행의 실제 정류장 통과 여부는 확인하지 못했다.')
    figure('supply_record_composition.png',195)
    t=supply['totals']
    para(f"현황 기록은 저상 확인 {t['low_floor_records']:,}행, 일반 확인 {t['regular_records']:,}행, 미확인 {t['unknown_records']:,}행이다. 기록 기준 분류 연결률은 63.3%다. 한 행을 완주 운행·승객 수·정류장 도착으로 간주하지 않았다.",'small')
    para('AI 기술 활용','sub',5)
    para('사용 서비스는 OpenAI Codex다. 공개 자료 검색·명세 확인, 수집·연결·검증 코드, 그림과 문서 초안에 활용했다. AI가 연료·좌표·효과를 임의로 채운 결과는 사용하지 않았다. 집계 대조·자동 검사·그림 검토를 수행했으며 미확인 사항은 한계로 명시했다.','small')
    para('주요 요청 요약: 교통약자와 탄소저감을 함께 고려할 수 있는 공개 데이터 탐색, 저상버스 관련 자료의 분석 가능성 검토, 확보한 자료를 활용한 분석과 보고서 정리. 이는 대화 원문 인용이 아니라 실제 요청의 요약이다.','small')
    pdf.showPage()

    review=json.loads((ROOT/'outputs/public/route_review_types.json').read_text(encoding='utf-8'))
    if review['route_count'] != 375: raise ValueError('Review population changed')
    start('본문 3 / 5');title('3. 노선 구성 차이와 전환 제약')
    para('과거 표본의 차량·노선 조합 수로 계산한 간선 사례의 조건부 저상 구성은 100번 70.0~100.0%, 104번 8.3~33.3%, 172번 0~25.9%였다. <b>100번의 하한이 104번의 상한보다 높아 미분류를 고려해도 두 노선의 구성 차이는 남는다.</b> 차량 구성과 기록 비중의 분모는 구분한다.')
    figure('lowfloor_composition_bounds.png',150)
    para('공식 예외승인표에는 25개 노선·235대가 있었다. 도로 조건 관련 59대, 충전·중형차 공급 조건 관련 192대는 16대가 겹쳐 합산하면 안 된다. 예외 목록에 없다는 사실이 즉시 교체 가능함을 보장하지 않는다.')
    figure('policy_constraints.png',130)
    para('검토 유형과 기준 민감도 (운행기록 비중 기준)','sub',4)
    table([['탐색 기준','낮은 구성 확인형','운영 제약 확인형','정보 보완형','하한 충족']]+[[str(r['percent'])+'%',r['counts']['low_composition'],r['counts']['operational_constraint'],r['counts']['information_needed'],r['counts']['lower_meets']] for r in review['thresholds']], [65,115,115,100,usable-395])
    para('앞의 두 유형은 상한이 기준 미만인 노선을 공식 예외승인 사유 유무로 나눈 것이다. 정보 보완형은 범위가 기준에 걸치며, 하한 충족은 이동 편의 충족을 뜻하지 않는다. 기준은 정책 기준이 아니다. 차량 구성 사례와 달리 3일 기록 수를 합산한 비중을 사용했다.','small',5)
    para(f"세 기준에서 모두 낮은 구성으로 분류된 노선은 {len(review['stable_low_below_30'])}개(예외 사유 없음 6개·있음 9개)였다. {review['threshold_sensitive_routes']}개는 기준에 따라 유형이 달라졌다. 이는 교체 순위가 아닌 추가 검토 유형이다.",'small',5)
    para('구성 차이는 사례 선택의 근거가 될 수 있으나 실제 대기시간·접근성 불이익·탄소효과를 입증하지 않는다. 현재 도로·차량규격·차고지 충전 조건과 기존 연료를 확인한 뒤 교체를 검토해야 한다.','small')
    pdf.showPage()

    start('본문 4 / 5');title('4. 보조 분석: 시설 연결과 위치 민감도')
    para(f"시설 274곳에서 좌표 후보 247곳을 얻었다. 도로명·건물번호가 일치한 {facility['address_matching_candidate_facilities']}곳을 노선 구성과 연결했으나 실제 건물·출입구 검수는 미완료다. 500m·탐색 기준 50%에서 하한 이상 노선 있음 232곳, 모든 연결노선 상한 미만 1곳, 불확실 4곳이었다.")
    figure('facility_supply_sensitivity.png',190)
    para('232곳은 이동 편의가 충분하다는 뜻이 아니라 조건을 충족하는 대상 노선이 하나 이상 있다는 뜻이다. 50%는 정책 기준이 아니다. 상한 미달 사례는 수어통역센터여서 휠체어 수요를 대표한다고 할 수 없다. 시설 종류별 연결률도 달랐다. 복지관 58곳 중 46곳, 주간이용시설 144곳 중 133곳이 연결돼 확인된 표본을 전체 수요로 일반화하지 않았다.','small')
    figure('gangbuk_building_sensitivity.png',184)
    para(f"강북장애인종합복지관의 두 주소 후보는 {location['coordinate_separation_metres']:.2f}m 차이였다. 한 정류장이 본관에서 301.0m, 별관에서 284.0m로 300m 경계 양쪽에 놓여 진단 범주가 바뀌었다. 한 시설의 두 위치 시나리오이며 시설 2곳으로 더하지 않았다. 실제 출입구·보행 경로 확인 전 취약지로 확정하지 않는다.",'small')
    pdf.showPage()

    start('본문 5 / 5');title('5. 우선 교체 검토 후보와 정책 제안')
    candidates=sorted([r for r in review['routes'] if r['review_type_by_threshold']['30']=='low_composition'], key=lambda r:(r['upper_bound'],r['route_id']))
    vehicle_rows=json.loads((ROOT/'outputs/public/lowfloor_linkage_authorization.json').read_text(encoding='utf-8'))['routes']
    vehicles={r['route_id']:r for r in vehicle_rows}
    if {r['route_name'] for r in candidates}!={'422','172','103','3317','2112','1137'}:
        raise ValueError('Candidate set changed: review the recommendation')
    para('<b>일반차량의 전기저상 전환을 우선 검토할 후보로 6개 노선을 제안한다.</b> 미확인 기록을 모두 저상으로 보아도 기록 비중 상한이 30% 미만이고, 확보한 공식 예외승인표와 연결되지 않은 노선이다. 30%는 탐색 기준이며 실제 교체 가능성을 보장하지 않는다.')
    candidate_table=[['노선','저상 기록 비중 범위','관측 차량: 저상/일반/미확인','저상 차량 구성 범위']]
    for r in candidates:
        v=vehicles[r['route_id']]
        low,regular,unknown,total=(v[k] for k in ['low_floor_vehicles','regular_vehicles','unclassified_vehicles','historical_vehicles'])
        if low+regular+unknown!=total: raise ValueError('Vehicle counts do not sum')
        candidate_table.append([r['route_name']+'번',f"{r['lower_bound']*100:.1f}~{r['upper_bound']*100:.1f}%",f'{low}/{regular}/{unknown}대',f'{100*low/total:.1f}~{100*(low+unknown)/total:.1f}%'])
    table(candidate_table,[45,130,190,usable-365])
    para('표는 기록 비중 상한 순으로 배열했으며 종합 교체 순위가 아니다. 기록 수와 관측 차량 수는 다른 분모다. 현재 차량 분류가 과거에도 유효하다는 조건이며 저상 확인 0대가 실제 저상차량 부재를 뜻하지 않는다.','small',6)
    para('<b>구체적 검토 사례는 422번과 172번이다.</b> 422번은 6개 후보 중 기록 비중 상한이 20.1%로 가장 낮고, 관측 차량도 일반 확인 12대·미확인 3대였다. 172번은 일반 확인 20대·미확인 7대로 비저상 대체를 검토할 차량이 확인됐다. 두 노선의 교체계획·잔여 차령·도로와 충전 조건을 먼저 확인하고, 일반차량의 전기저상 전환 가능성을 검토할 것을 제안한다.')
    para('검토 결과의 활용','sub',5)
    para('① 위 6개는 차량 구성·교체계획을 확인한다. 별도로 낮은 비중과 공식 제약이 함께 확인된 9개는 도로·충전·차종 제약부터 검토한다. ② 정보 보완형은 차량 분류부터 보완한다. ③ 실제 시설 출입구·이동 방향·대안 노선을 확인한 뒤 교체 대상을 결정한다. 시설 분석을 422번·172번의 수요 우위 근거로 사용하지 않았다.','small')
    para('전기저상 도입 실적은 <b>기존 저상차량 대체 / 비저상차량 대체</b>로 나누고 친환경 도입 대수와 저상차량 순증을 함께 공개한다. 비저상 대체는 저상차량 수를 늘릴 여지가 있다. 탄소효과는 기존 동력원·운행거리 등을 확인해 별도로 평가해야 한다.','small')
    table([['핵심 한계','제안의 범위'],
           ['3일 표본·현재 분류의 과거 적용','조건부 검토 후보; 확정 교체 순위 아님'],
           ['기존 연료·정의가 확인된 주행거리 미확보','탄소감축량·탄소효율 순위 미산출'],
           ['수요·보행 경로·실측 도착 미확인','수혜 인원·접근성 효과·대기시간 미산출']], [185,usable-185])
    para('분석도구와 코드','sub',5)
    para('Python 3.12, 표준 라이브러리, matplotlib를 사용했다. 재현 명령은 docs/reproduce.md에 있다. 당시 실시간 분류 스냅샷을 보관해야 같은 결과를 재현할 수 있으며 현재 API 재호출로 동일 표본이 되지 않는다. 인증키·원본 행 단위 자료는 Git에서 제외했다.','small')
    repo='https://github.com/daara0322/TransportationData/tree/codex/supply-analysis'
    para('코드 링크: '+link(repo)+'<br/><b>공개 저장소:</b> 2026-10-20 로그인 없는 분석 브랜치 README 접근을 확인했다. 원자료·인증키는 제외했으며 당시 스냅샷의 재현 한계는 실행 안내에 설명했다. 보관한 입력의 내부 재실행과 제3자의 원본 재확보 검증은 구분한다.','small')
    pdf.showPage()

    start('참고자료');title('참고자료')
    references=[
        ('공고·참가신청서·보고서 양식 / 숲과나눔','https://koreashe.org/notice/?uid=95427&mod=document&pageid=1'),
        ('차량 운행통계 / 서울시 BIS·T-Data','https://t-data.seoul.go.kr/dataprovide/trafficdataviewfile.do?data_id=84'),
        ('노선 마스터·노선 상세·경유노드·차량별노선·정류장 / T-Data','https://t-data.seoul.go.kr/dataprovide/trafficdataviewfile.do?data_id='),
        ('버스위치정보 / 서울시·공공데이터포털','https://www.data.go.kr/data/15000332/openapi.do'),
        ('인가현황 / 서울시','https://news.seoul.go.kr/traffic/archives/6838'),
        ('저상버스 예외승인 / 서울시','https://news.seoul.go.kr/traffic/archives/513625'),
        ('버스 현황 / 서울시','https://news.seoul.go.kr/traffic/archives/300'),
        ('장애인지역사회재활시설 목록 / 서울시·열린데이터광장','https://data.seoul.go.kr/dataList/OA-20429/A/1/datasetView.do'),
        ('주소 검색 / 카카오디벨로퍼스','https://developers.kakao.com/docs/ko/kakaomap/common'),
        ('강북장애인종합복지관 본관 주소 / 한국장애인개발원','https://vr.koddi.or.kr/org/org_info_view.jsp?orgCd=123456789000051&seOrgKnd1=1&seSysType=vr'),
    ]
    for label,url in references:
        if url.endswith('data_id='):
            para('<b>'+escape(label)+'</b><br/>'+'<br/>'.join(link(url+str(i)) for i in [53,54,58,60,64]),'small',8)
        else:para('<b>'+escape(label)+'</b><br/>'+link(url),'small',8)
    para('출처의 기준일은 다르다. 운행통계 10/13~15, 현재 차량 분류 10/17, 시설 페이지 갱신일 9/23, 버스 현황은 1월이다. 원본별 수집일·해시와 상세 이용조건은 data/README.md와 data/manifest.json을 대조한다.','small')
    para('추가 분석의 탐색 기준은 30·50·80%이며 법적·정책적 적정 수준을 의미하지 않는다. 낮은 구성 유형의 안정성은 이 세 기준에 한정된다. 세 기준 모두에서 불확실한 노선도 있으므로 유형 유지와 정보 충분성을 구분한다. 상세 노선별 결과는 outputs/public/route_review_types.json에 있다.','small')
    pdf.save()
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default=str(ROOT/'output/pdf/analysis_review_draft.pdf'))
    parser.add_argument('--font',default='C:/Windows/Fonts/malgun.ttf')
    parser.add_argument('--bold-font',default='C:/Windows/Fonts/malgunbd.ttf')
    parser.add_argument('--profile',help='Local JSON profile; personalized output must stay in data/processed/submission/')
    args=parser.parse_args()
    print(build(args.output,args.font,args.bold_font,args.profile))
