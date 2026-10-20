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


def build(output,font_path,bold_path):
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
    pdf=canvas.Canvas(str(target),pagesize=A4,pageCompression=1)
    pdf.setTitle('서울 버스 전환 분석 - 검토용 초안, 탄소 전환안 미산출')
    pdf.setAuthor('검토용 초안 - 이름 미입력')
    width,height=A4
    left=46; usable=width-left*2;y=height-61
    def start(label):
        nonlocal y
        y=height-61
        pdf.setFillColor(MUTED);pdf.setFont('Korean',8)
        pdf.drawString(left,height-30,'TransportationData / 검토용 초안 / 2026-10-20')
        pdf.setStrokeColor(colors.HexColor('#d8e1e6'));pdf.line(left,43,width-left,43)
        pdf.drawString(left,29,'탄소 전환안·현장 접근성 검증 미완료 / 최종 제출본 아님')
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
    para('검토용 보고서','sub',26)
    para('탄소저감과 교통약자 접근성을<br/>함께 고려한 서울 버스 전환 분석','cover',24)
    para('현재 확보 자료의 분석 결과와 미충족 입력 점검','sub',28)
    para('<b>이름 / 소속:</b> 본인 직접 입력 필요',gap=16)
    para('<b>문서 상태:</b> 검토용 초안. 원래 계획의 탄소감축량과 동일 교체 대수 비교안은 아직 산출하지 않았다. 최종 출품 주제와 해석은 본인 검토가 필요하다.',gap=18)
    table([['확인한 분석','현재 확인하지 못한 것'],
           ['375개 후보 노선의 112,864행 운행기록 구성<br/>시설 좌표 후보와 주변 노선의 조건부 연결<br/>대표 위치·반경 민감도','차량별 연료와 거리의 공식 정의<br/>과거 저상 분류 유효성<br/>실제 통행 수요·출입구·정류장 도착 간격']], [usable/2]*2)
    para('표지 + 본문 5쪽 + 참고자료 1쪽으로 구성했다. 신청서의 개인정보·동의·서명은 작성하지 않았다. 인증키와 원본 행 단위 자료는 문서에 포함하지 않았다.','small')
    pdf.showPage()

    start('본문 1 / 5');title('1. 분석 배경·목적과 활용 데이터')
    para('전기저상버스 도입은 운행 배출과 승하차 편의를 함께 바꿀 수 있다. 그러나 기존 저상차량을 전기저상으로 교체하면 저상 이용 기회의 증분은 0일 수 있다. 두 효과를 구분하고, 자료가 허용하는 범위에서 전환 검토 근거를 만드는 것이 분석 목적이다.')
    para('<b>참여 동기:</b> 본인의 실제 참여 동기는 최종 원고에서 직접 작성해야 한다. 기존 정책이 불공정하다는 결론은 전제하지 않았다.','small')
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
    para('사용 서비스는 OpenAI Codex다. 공개 자료 검색·명세 확인, 수집·연결·검증 코드, 그림과 문서 초안에 활용했다. AI가 연료·좌표·효과를 임의로 채운 결과는 사용하지 않았다. 본인의 최종 원문·결과 검토는 아직 남아 있다.','small')
    para('주요 실제 요청: “얻을수있는 데이터에서 다른팀이 하지않을거같은 생소한 문제점 찾아줘봐”, “쭉가보자 계획 짠거 확인하면서 진행해줘 앞으로 진행해야될거 체크리스트 만들어서 쭉해줘”. 전체 활용 기록은 docs/ai_usage.md에 있다.','small')
    pdf.showPage()

    start('본문 3 / 5');title('3. 노선 구성 차이와 전환 제약')
    para('과거 표본의 차량·노선 조합 수로 계산한 간선 사례의 조건부 저상 구성은 100번 70.0~100.0%, 104번 8.3~33.3%, 172번 0~25.9%였다. 차량 대수 구성과 운행기록 비중은 서로 다른 분모이므로 구분한다.')
    figure('lowfloor_composition_bounds.png',205)
    para('공식 예외승인표에는 25개 노선·235대가 있었다. 도로 조건 관련 59대, 충전·중형차 공급 조건 관련 192대는 16대가 겹쳐 합산하면 안 된다. 예외 목록에 없다는 사실이 즉시 교체 가능함을 보장하지 않는다.')
    figure('policy_constraints.png',205)
    para('구성 차이는 사례 선택의 근거가 될 수 있으나 실제 대기시간·접근성 불이익·탄소효과를 입증하지 않는다. 현재 도로·차량규격·차고지 충전 조건과 기존 연료를 확인한 뒤 교체를 검토해야 한다.','small')
    pdf.showPage()

    start('본문 4 / 5');title('4. 시설 연결과 위치 민감도')
    para(f"시설 274곳에서 좌표 후보 247곳을 얻었다. 도로명·건물번호가 일치한 {facility['address_matching_candidate_facilities']}곳을 노선 구성과 연결했으나 실제 건물·출입구 검수는 미완료다. 500m·탐색 기준 50%에서 하한 이상 노선 있음 232곳, 모든 연결노선 상한 미만 1곳, 불확실 4곳이었다.")
    figure('facility_supply_sensitivity.png',190)
    para('50%는 정책 기준이 아니다. 상한 미달 사례는 수어통역센터여서 휠체어 수요를 대표한다고 할 수 없다. 시설 종류별 연결률도 달랐다. 복지관 58곳 중 46곳, 주간이용시설 144곳 중 133곳이 연결돼 확인된 표본을 전체 수요로 일반화하지 않았다.','small')
    figure('gangbuk_building_sensitivity.png',184)
    para(f"강북장애인종합복지관의 두 주소 후보는 {location['coordinate_separation_metres']:.2f}m 차이였다. 한 정류장이 본관에서 301.0m, 별관에서 284.0m로 300m 경계 양쪽에 놓여 진단 범주가 바뀌었다. 한 시설의 두 위치 시나리오이며 시설 2곳으로 더하지 않았다. 실제 출입구·보행 경로 확인 전 취약지로 확정하지 않는다.",'small')
    pdf.showPage()

    start('본문 5 / 5');title('5. 정책 검토 방향·기대효과와 한계')
    para('첫째, 친환경 차량 도입 실적과 저상 운행의 증가를 구분해 제시한다. 기존 저상차량을 바꾸는 전환과 비저상차량을 바꾸는 전환을 나눠야 두 목표의 증분을 평가할 수 있다. 현재는 연료·거리 정의가 없어 감축량과 최종 순위를 제시하지 않았다.')
    para('둘째, 단일 비율 대신 분류 연결률과 미확인 범위를 함께 공개한다. 노선 ID·기준일·동력원·저상 여부를 연결할 수 있는 자료가 제공되면 교체 후보 검토의 추적 가능성이 높아질 수 있다. 추가 이용자 수나 감축량의 정량 기대효과는 아직 검증하지 않았다.')
    para('셋째, 반경에 포함된 정류장 유무만으로 시설의 접근성을 확정하지 않는다. 대표 건물·출입구, 실제 목적지와 방향, 다른 노선유형과 송영차량, 예외승인 제약을 함께 확인한다. 약 42m 차이로 범주가 달라진 사례는 입력 위치의 검수 필요성을 보여준다.')
    table([['미확인 입력','현재 가능한 판단과 제한'],
           ['차량·노선별 기존 연료','실제 탄소감축량·탄소 중심 순위 산출 불가'],
           ['거리 단위·한 행 정의','미터 규모를 지지하는 대조만 수행; 공식 km 실적 미확정'],
           ['현재 저상 분류의 과거 유효성','과거 저상 구성은 조건부 범위로만 제시'],
           ['시설 위치·통행 특성','미검수 후보·시설 종류만 확보; 수혜 인원 미산출'],
           ['정류장별 실제 도착 시각','배차 이력의 의미 확인 전 대기시간 미산출']], [145,usable-145])
    para('자료가 확보되면 기준일·연결키·누락·단위를 검증한 뒤 같은 교체 대수의 탄소 중심·접근성 중심·공동안을 비교한다. 확보하지 못하면 실제 감축효과를 계산한 연구로 제출하지 않으며 주제 범위를 본인이 다시 결정해야 한다. 현재 문서는 그 결정을 위한 검토본이다.')
    para('분석도구와 코드','sub',5)
    para('Python 3.12, 표준 라이브러리, matplotlib를 사용했다. 재현 명령은 docs/reproduce.md에 있다. 당시 실시간 분류 스냅샷을 보관해야 같은 결과를 재현할 수 있으며 현재 API 재호출로 동일 표본이 되지 않는다. 인증키·원본 행 단위 자료는 Git에서 제외했다.','small')
    repo='https://github.com/daara0322/TransportationData/tree/codex/supply-analysis'
    para('코드 링크: '+link(repo)+'<br/><b>현재 비공개:</b> 심사자 접근 방법·제출 범위는 본인이 결정해야 한다. 로그아웃 접근 검증과 최종 깨끗한 환경 재현은 미완료다.','small')
    pdf.showPage()

    start('참고자료');title('참고자료와 제출 전 확인')
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
    para('<b>미완료:</b> 이름·참여 동기·신청서·동의·서명, 최종 연구 범위, 탄소 입력, 코드 접근 방법과 원본 확보 재현. 이 문서는 제출 승인이나 최종 보고서 완성을 뜻하지 않는다.','small')
    pdf.save()
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default=str(ROOT/'output/pdf/analysis_review_draft.pdf'))
    parser.add_argument('--font',default='C:/Windows/Fonts/malgun.ttf')
    parser.add_argument('--bold-font',default='C:/Windows/Fonts/malgunbd.ttf')
    args=parser.parse_args()
    print(build(args.output,args.font,args.bold_font))
