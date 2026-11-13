"""Generate self-hosted SVG profile cards from public GitHub data. Python stdlib only."""
import os, json, math, sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from html import escape
from urllib.request import Request, urlopen
USER='Ravindu200324511398'
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'
COLORS=['#b0e56b','#38d9dc','#71c9fa','#b8a1ed','#f4ce76','#ed9f86']
def api(path, payload=None):
    token=os.environ['GH_TOKEN']
    req=Request('https://api.github.com/'+path, data=json.dumps(payload).encode() if payload else None, headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'ravindu-profile','Content-Type':'application/json'})
    with urlopen(req,timeout=60) as r: data=json.load(r)
    if isinstance(data,dict) and data.get('errors'): raise RuntimeError(str(data['errors']))
    return data

def text(x,y,value,size=17,color='#e4eee0',anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="monospace" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(value))}</text>'

def card(name,title,body,w=1000,h=260,subtitle=''):
    OUT.mkdir(exist_ok=True)
    value=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" fill="#0d1518" stroke="#304532"/>'+text(28,38,title,20,'#b0e56b')+text(28,61,subtitle,11,'#8baca5')+body+'</svg>'
    (OUT/(name+'.svg')).write_text(value)

def placeholder(name,title,w=1000):
    card(name,title,text(28,118,'Awaiting first GitHub Actions run',16)+text(28,151,'Activity data will appear after setup.',12,'#8baca5'),w,195)

def donut(name,title,counts,subtitle):
    entries=Counter({k:v for k,v in counts.items() if v>0}).most_common()
    if len(entries)>6: entries=entries[:5]+[('Other',sum(v for _,v in entries[5:]))]
    total=sum(v for _,v in entries)
    body=''; offset=0; circum=2*math.pi*68
    if not total: body=text(28,130,'No public activity in this window.',14)
    else:
        for i,(label,n) in enumerate(entries):
            length=n/total*circum
            body+=f'<circle cx="123" cy="170" r="68" fill="none" stroke="{COLORS[i]}" stroke-width="24" stroke-dasharray="{length} {circum-length}" stroke-dashoffset="{-offset}" transform="rotate(-90 123 170)"/>'
            offset+=length
            body+=f'<rect x="230" y="{97+i*27}" width="9" height="9" rx="2" fill="{COLORS[i]}"/>'+text(249,106+i*27,label[:17],12)+text(465,106+i*27,f'{n/total:.1%}',12,'#8baca5','end')
        body+=text(123,166,'PUBLIC',11,'#8baca5','middle')+text(123,188,str(total) if total<10000 else 'CODE',19,'#e4eee0','middle')
    card(name,title,body,500,280,subtitle)

def streaks(days):
    longest=run=0
    for day in days:
        run=run+1 if day['contributionCount'] else 0
        longest=max(longest,run)
    tail=days[:]
    # A still-open current calendar day does not break yesterday's streak.
    today=datetime.now(timezone.utc).date().isoformat()
    if tail and tail[-1]['date']==today and not tail[-1]['contributionCount']: tail.pop()
    current=0
    for day in reversed(tail):
        if not day['contributionCount']: break
        current+=1
    return current,longest

def main():
    if '--placeholders' in sys.argv:
        for name,title,w in [('stats','GitHub Stats',1000),('streak','Contribution Streak',1000),('languages','Most Used Languages',1000),('languages-commits','Languages by Commit',500),('languages-repos','Languages by Repository',500),('contribution-snake','Contribution Snake',1000)]: placeholder(name,title,w)
        return
    profile=api('users/'+USER)
    repos=[]; page=1
    while True:
        batch=api(f'users/{USER}/repos?type=owner&per_page=100&page={page}')
        repos+=batch
        if len(batch)<100: break
        page+=1
    own=[r for r in repos if not r['fork']]
    languages=Counter(); repo_languages=Counter()
    for repo in own:
        if repo.get('language'): repo_languages[repo['language']]+=1
        for lang,size in api(f'repos/{USER}/{repo["name"]}/languages').items(): languages[lang]+=size
    query='''query($login:String!){ user(login:$login){ contributionsCollection { totalCommitContributions totalIssueContributions totalPullRequestContributions totalRepositoriesWithContributedCommits contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } commitContributionsByRepository(maxRepositories:100) { repository { primaryLanguage { name } } contributions { totalCount } } } } }'''
    c=api('graphql',{'query':query,'variables':{'login':USER}})['data']['user']['contributionsCollection']
    commit_languages=Counter()
    for item in c['commitContributionsByRepository']:
        lang=item['repository']['primaryLanguage']
        commit_languages[lang['name'] if lang else 'Unclassified']+=item['contributions']['totalCount']
    stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    values=[('Public repositories',profile['public_repos']),('Stars on owned repos',sum(r['stargazers_count'] for r in own)),('Followers',profile['followers']),('Commits / last year',c['totalCommitContributions']),('PRs / last year',c['totalPullRequestContributions']),('Issues / last year',c['totalIssueContributions'])]
    body=''
    for i,(label,n) in enumerate(values):
        x=30+(i%3)*325; y=107+(i//3)*88
        body+=text(x,y,label,13,'#8baca5')+text(x,y+39,f'{n:,}',30,COLORS[i%3])
    card('stats','Ravindu’s GitHub Stats',body,subtitle='Public GitHub activity • Updated '+stamp,h=280)
    days=[d for w in c['contributionCalendar']['weeks'] for d in w['contributionDays']]
    current,longest=streaks(days)
    body=''
    for i,(label,n) in enumerate([('Contributions / last year',c['contributionCalendar']['totalContributions']),('Current streak / days',current),('Longest streak / days',longest)]):
        x=30+i*325
        body+=text(x,108,label,13,'#8baca5')+text(x,154,n,32,COLORS[i])
    card('streak','Contribution Streak',body,h=190,subtitle='GitHub contribution calendar • Last-year window')
    # Horizontal language composition bar with an explicit byte-based denominator.
    entries=languages.most_common(8); total=sum(languages.values())
    if len(languages)>8: entries=languages.most_common(7)+[('Other',sum(v for _,v in languages.most_common()[7:]))]
    body=''; x=30
    if total:
        for i,(label,n) in enumerate(entries):
            width=n/total*940
            body+=f'<rect x="{x}" y="88" width="{width}" height="18" fill="{COLORS[i%6]}"/>'; x+=width
            body+=text(30+(i%4)*240,145+(i//4)*35,f'{label} {n/total:.1%}',13,COLORS[i%6])
    else: body=text(30,120,'No language data available yet.')
    card('languages','Most Used Languages',body,h=215,subtitle='Code bytes in public, non-fork repositories')
    donut('languages-commits','Languages by Commit',commit_languages,'Last year • Grouped by repository primary language')
    donut('languages-repos','Languages by Repository',repo_languages,'Public, non-fork repositories • Primary language')

if __name__=='__main__': main()
