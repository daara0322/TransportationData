"""Render a conditional composition diagnostic from public aggregates."""
import argparse
import json
from pathlib import Path


def render(source,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    fonts={font.name for font in font_manager.fontManager.ttflist}
    for name in ['Malgun Gothic','Noto Sans CJK KR','AppleGothic']:
        if name in fonts:
            plt.rcParams['font.family']=name
            break
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':11,
                         'axes.spines.top':False,'axes.spines.right':False,
                         'axes.spines.left':False})
    data=json.loads(Path(source).read_text(encoding='utf-8'))
    fig,ax=plt.subplots(figsize=(11.5,6.3))
    labels=['하한 50% 이상인 노선 있음','판단 불확실','모든 연결노선 상한 50% 미만','범위 내 대상 노선 없음']
    colors=['#187d8b','#e3bd77','#b76659','#dce1e6']
    for y,group in enumerate(data['by_radius']):
        check=next(c for c in group['threshold_checks'] if c['threshold']==.5)
        values=[check['lower_bound_meets'],check['uncertain'],check['upper_bound_below'],group['no_nearby_route']]
        left=0
        for index,(value,label,color) in enumerate(zip(values,labels,colors)):
            ax.barh(y,value,left=left,color=color,height=.48,label=label if y==0 else None)
            if value>=12:
                ax.text(left+value/2,y,str(value),ha='center',va='center',color='white' if index==0 else '#26323b')
            left+=value
        ax.text(241,y,' / '.join(str(v) for v in values),va='center',fontsize=10)
    ax.set_yticks(range(len(data['by_radius'])),[str(g['radius_metres'])+'m' for g in data['by_radius']])
    ax.invert_yaxis();ax.set_ylim(2.6,-.6)
    ax.set_xlim(0,275);ax.set_xticks([0,50,100,150,200,237])
    ax.tick_params(axis='y',length=0);ax.set_axisbelow(True);ax.grid(axis='x',alpha=.16)
    ax.set_xlabel('시설 수 · 도로명·건물번호 일치 후보 237곳')
    fig.suptitle('주변 노선의 기록 구성을 연결한 사전 진단',x=.08,y=.96,ha='left',fontsize=18,fontweight='bold')
    fig.text(.08,.86,'노선 전체 운행기록의 저상 비중 · 50%는 탐색용 기준이며 서비스 기준이 아님',color='#52606d')
    ax.legend(loc='upper left',bbox_to_anchor=(0,-.27),ncol=2,frameon=False,fontsize=10)
    fig.text(.08,.065,'미검수 시설 좌표·직선거리·선정한 375개 노선에 한정. 미분류 차량은 하한·상한에 반영.\n해당 정류장의 도착 비율·대기시간·목적지 연결·휠체어 수요·탄소효과를 확인한 결과가 아니다.',
             fontsize=9,color='#52606d',linespacing=1.6)
    fig.subplots_adjust(left=.08,right=.94,top=.78,bottom=.36)
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(target,dpi=180,facecolor='white');plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default='outputs/public/facility_supply_diagnostic.json')
    parser.add_argument('--output',default='outputs/public/figures/facility_supply_sensitivity.png')
    args=parser.parse_args();render(args.source,args.output)
