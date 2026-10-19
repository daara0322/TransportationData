"""Render the distance-boundary example from public scenario aggregates."""
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
            plt.rcParams['font.family']=name;break
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':11,
                         'axes.spines.top':False,'axes.spines.right':False})
    data=json.loads(Path(source).read_text(encoding='utf-8'))
    rows=[]
    for identifier in ['C5044_main_scenario','C5044_annex_scenario']:
        scenario=next(s for s in data['scenarios'] if s['scenario_id']==identifier)
        group=next(g for g in scenario['by_radius'] if g['radius_metres']==500)
        distance=next(r['nearest_station_metres'] for r in group['routes'] if r['route_name']=='1111')
        bounds=next(g for g in scenario['by_radius'] if g['radius_metres']==300)
        rows.append((distance,bounds['best_route_share_lower']*100,bounds['best_route_share_upper']*100))
    fig,axes=plt.subplots(1,2,figsize=(11.5,5.8),gridspec_kw={'width_ratios':[1.1,1]})
    colors=['#b76757','#177e8c']
    for y,(distance,lower,upper) in enumerate(rows):
        axes[0].barh(y,distance,height=.35,color=colors[y])
        axes[0].text(distance+4,y,f'{distance:.1f}m',va='center',fontsize=11)
        axes[1].plot([lower,upper],[y,y],lw=12,color=colors[y],solid_capstyle='round')
        axes[1].text((lower+upper)/2,y-.2,f'{lower:.2f}~{upper:.2f}%',ha='center',fontsize=11)
    for ax in axes:
        ax.set_yticks([0,1],['본관 주소 후보','별관 주소 후보']);ax.set_ylim(1.55,-.55)
        ax.tick_params(axis='y',length=0);ax.spines['left'].set_visible(False)
    axes[0].axvline(300,color='#697780',ls='--',lw=1)
    axes[0].set_xlim(0,365);axes[0].set_xlabel('1111번 최근접 대상 정류장까지 직선거리(m)')
    axes[0].set_title('300m 경계의 양쪽에 놓이는 정류장',fontsize=12,pad=20)
    axes[1].set_xlim(0,105);axes[1].set_xticks([0,25,50,75,100],['0','25','50','75','100%'])
    axes[1].set_xlabel('300m 연결 노선 구성의 하한~상한')
    axes[1].set_title('노선 전체 기록 구성의 진단 변화',fontsize=12,pad=20)
    fig.suptitle('약 42m의 대표점 차이로 달라진 300m 진단',x=.07,y=.96,ha='left',fontsize=18,fontweight='bold')
    fig.text(.07,.85,'강북장애인종합복지관 1곳의 두 주소 시나리오 · 건물·출입구 미검수',color='#52606d')
    fig.text(.07,.07,'오른쪽은 정류장 도착비율이나 대기시간이 아닌 노선 전체 기록의 조건부 범위다.\n별관의 실제 이용 기능·출입구와 보행 경로는 미확인. 두 시나리오를 시설 2곳으로 합산하지 않았다.',fontsize=9,color='#52606d',linespacing=1.6)
    fig.subplots_adjust(left=.13,right=.97,top=.68,bottom=.27,wspace=.5)
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(target,dpi=180,facecolor='white');plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default='outputs/public/gangbuk_building_sensitivity.json')
    parser.add_argument('--output',default='outputs/public/figures/gangbuk_building_sensitivity.png')
    args=parser.parse_args();render(args.source,args.output)
