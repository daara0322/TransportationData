"""Render descriptive figures from validated aggregates and policy facts."""
import argparse
import json
from collections import Counter
from pathlib import Path


def render(supply_path, master_path, output_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    fonts = {font.name for font in font_manager.fontManager.ttflist}
    for name in ['Malgun Gothic', 'Noto Sans CJK KR', 'AppleGothic']:
        if name in fonts:
            plt.rcParams['font.family'] = name
            break
    plt.rcParams.update({'axes.unicode_minus': False, 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.spines.left': False, 'figure.facecolor': '#ffffff'})
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    supply = json.loads(Path(supply_path).read_text(encoding='utf-8'))
    groups = {}
    for item in supply['by_type_day']:
        key = (item['route_type'], item['service_group'])
        groups.setdefault(key, Counter()).update({k:item[k] for k in ['records','low_floor_records','regular_records','unknown_records']})
    fig, ax = plt.subplots(figsize=(10, 5.4))
    names = {'3':'간선 후보', '4':'지선 후보'}
    colors = ['#167d8d', '#d39140', '#dce1e6']
    for y, ((kind, group), counts) in enumerate(sorted(groups.items())):
        left = 0
        for field, label, color in zip(['low_floor_records','regular_records','unknown_records'],
                                       ['저상 확인','일반 확인','미확인'], colors):
            percent = counts[field]/counts['records']*100
            ax.barh(y, percent, left=left, height=.42, color=color,
                    label=label if y==0 else None,
                    hatch='///' if field=='unknown_records' else None,
                    edgecolor='#ffffff' if field!='unknown_records' else '#b5bdc5', linewidth=.6)
            if percent>=5:
                ax.text(left+percent/2,y,f'{percent:.1f}%',ha='center',va='center',
                        color='#ffffff' if field=='low_floor_records' else '#202b33')
            left += percent
        group_label = '심야 명칭' if group=='night_name' else '주간·맞춤 등'
        ax.text(101,y,f"{counts['records']:,}행",va='center',fontsize=10)
    labels=[names[k]+'\n'+('심야 명칭' if g=='night_name' else '주간·맞춤 등') for k,g in sorted(groups)]
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlim(0,114)
    ax.set_xticks([0,25,50,75,100], ['0','25','50','75','100%'])
    ax.set_ylim(-.65,len(labels)-.35)
    ax.invert_yaxis()
    ax.tick_params(axis='y',length=0)
    ax.set_axisbelow(True)
    ax.grid(axis='x',alpha=.15)
    ax.legend(loc='upper left',bbox_to_anchor=(0,1.25),ncol=3,frameon=False)
    fig.suptitle('운행기록에 연결한 저상 분류 현황',x=.08,ha='left',fontsize=17,fontweight='bold',y=.98)
    fig.text(.08,.875,f"2026.10.13~15 · 검증된 후보 {supply['eligible_routes']}개 · 운행통계 {supply['totals']['records']:,}행",color='#52606d')
    fig.text(.08,.065,'현재 API의 저상 분류를 과거 운행기록에 조건부로 연결한 결과다. 전체 서울 노선의 보급률이 아니다.\n한 행은 검증된 완주 운행이나 승객 수가 아니며, 미확인 기록을 일반버스로 처리하지 않았다.',fontsize=9,color='#52606d',linespacing=1.6)
    fig.subplots_adjust(left=.16,right=.90,top=.69,bottom=.23)
    for ext in ['png']:
        fig.savefig(output/f'supply_record_composition.{ext}',dpi=180)
    plt.close(fig)

    audit=json.loads(Path(master_path).read_text(encoding='utf-8'))
    chosen=[next(r for r in audit['routes'] if r['candidate_name']==name and r['master_name']==name) for name in ['100','104','172']]
    fig,ax=plt.subplots(figsize=(10,5.6))
    for y,row in enumerate(chosen):
        low=row['low_floor_share_lower_bound']*100
        high=row['low_floor_share_upper_bound']*100
        ax.plot([low,high],[y,y],lw=14,color='#c4e2e7',solid_capstyle='round')
        ax.scatter([low,high],[y,y],s=55,color='#167d8d',zorder=3)
        ax.text((low+high)/2,y-.19,f'{low:.1f}~{high:.1f}%',ha='center',color='#145663')
    ax.set_yticks(range(3),[r['candidate_name']+'번' for r in chosen])
    ax.set_xlim(-2,102);ax.set_ylim(-.65,2.6);ax.invert_yaxis()
    ax.set_xticks([0,25,50,75,100],['0','25','50','75','100%'])
    ax.tick_params(axis='y',length=0);ax.set_axisbelow(True);ax.grid(axis='x',alpha=.18)
    ax.set_xlabel('관측된 과거 차량·노선 조합에서 가능한 저상 구성 비율')
    fig.suptitle('미확인 차량을 고려해도 남는 구성 차이',x=.08,ha='left',fontsize=17,fontweight='bold',y=.98)
    fig.text(.08,.88,'미확인 전부가 일반인 경우 ~ 전부가 저상인 경우 · 간선 사례 3개',color='#52606d')
    fig.text(.08,.055,'2026.10.17의 차량 분류가 10.13~15에도 유효하다는 조건이 필요하다.\n신뢰구간·실제 배차 간격·교체 우선순위가 아니다. 사례는 구성 차이를 설명하기 위해 선택했다.',fontsize=9,color='#52606d',linespacing=1.6)
    fig.subplots_adjust(left=.16,right=.94,top=.77,bottom=.24)
    for ext in ['png']:
        fig.savefig(output/f'lowfloor_composition_bounds.{ext}',dpi=180)
    plt.close(fig)
    import csv
    with Path('configs/lowfloor_exceptions_2026.csv').open(encoding='utf-8',newline='') as stream:
        exceptions=list(csv.DictReader(stream))
    road=sum(int(r['approved_buses']) for r in exceptions if r['primary_constraint']!='charging_and_medium_bus_supply')
    overlap=sum(int(r['additional_charging_overlap_buses']) for r in exceptions)
    charging=sum(int(r['approved_buses']) for r in exceptions if r['primary_constraint']=='charging_and_medium_bus_supply')+overlap
    total=sum(int(r['approved_buses']) for r in exceptions)
    if len({r['route_name'] for r in exceptions})!=len(exceptions) or road+charging-overlap!=total:
        raise ValueError('Inconsistent exception facts')
    fig,ax=plt.subplots(figsize=(10,5.6))
    labels=['충전·중형차 공급 조건','교량·경사·도로 폭','두 조건에 중복 해당']
    for y,(value,color) in enumerate(zip([charging,road,overlap],['#167d8d','#d39140','#8e9daa'])):
        ax.barh(y,value,height=.48,color=color)
        ax.text(value+3,y,f'{value}대',va='center')
    ax.set_yticks(range(3),labels);ax.set_xlim(0,240);ax.set_ylim(-.65,2.65);ax.invert_yaxis()
    ax.set_xticks([0,50,100,150,200]);ax.tick_params(axis='y',length=0)
    ax.set_axisbelow(True);ax.grid(axis='x',alpha=.15)
    fig.suptitle('저상버스 교체에는 운영 제약도 함께 걸려 있다',x=.08,ha='left',fontsize=17,fontweight='bold',y=.98)
    fig.text(.08,.88,f'서울시 2026년 예외승인 게시용 표 · {len(exceptions)}개 노선 · {total}대',color='#52606d')
    fig.text(.08,.05,f'출처: 서울시 저상버스 예외승인 현황. 중복 {overlap}대는 총 {total}대에 이미 포함돼 있다.\n표의 승인 사유를 요약한 값으로 현재의 시설 유무·교체 가능성을 확정하지 않는다.',fontsize=9,color='#52606d',linespacing=1.6)
    fig.subplots_adjust(left=.30,right=.94,top=.76,bottom=.23)
    for ext in ['png']:
        fig.savefig(output/f'policy_constraints.{ext}',dpi=180)
    plt.close(fig)
    return [str(output/name) for name in ['supply_record_composition.png','lowfloor_composition_bounds.png','policy_constraints.png']]


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supply',default='outputs/public/supply_records.json')
    parser.add_argument('--master-audit',default='outputs/public/route_master_audit.json')
    parser.add_argument('--output-dir',default='outputs/public/figures')
    args=parser.parse_args()
    print(json.dumps(render(args.supply,args.master_audit,args.output_dir)))
