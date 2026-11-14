import io
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import pdfplumber
import requests
from bs4 import BeautifulSoup

PAGE = 'https://official.nba.com/nba-injury-report-2026-27-season/'
PDF_RX = re.compile(r'Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{1,2})_(\d{2})(AM|PM)\.pdf', re.I)
STATUSES = 'Questionable|Available|Doubtful|Probable|Out'
PLAYER_RX = re.compile(r"(?P<last>[A-Za-zÀ-ÿ.'’\-]+),(?P<first>[A-Za-zÀ-ÿ.'’\-]+)\s+(?P<status>" + STATUSES + r")\b",re.I)
HEADER_RX = re.compile(r'^Injury Report:|^GameDate\s|^Page\d+of\d+', re.I)
# A team line on this pdf is a concatenated official team name, sometimes prefixed with matchup/time.
TEAMS = [
'AtlantaHawks','BostonCeltics','BrooklynNets','CharlotteHornets','ChicagoBulls',
'ClevelandCavaliers','DallasMavericks','DenverNuggets','DetroitPistons',
'GoldenStateWarriors','HoustonRockets','IndianaPacers','LAClippers','LosAngelesLakers',
'MemphisGrizzlies','MiamiHeat','MilwaukeeBucks','MinnesotaTimberwolves',
'NewOrleansPelicans','NewYorkKnicks','OklahomaCityThunder','OrlandoMagic',
'Philadelphia76ers','PhoenixSuns','PortlandTrailBlazers','SacramentoKings',
'SanAntonioSpurs','TorontoRaptors','UtahJazz','WashingtonWizards'
]
TEAM_RX = re.compile('|'.join(sorted(map(re.escape,TEAMS),key=len,reverse=True)))
SESSION = requests.Session()
SESSION.headers.update({'User-Agent':'Mozilla/5.0 (compatible; CizgiMasasiUpdater/1.0)','Accept':'text/html,application/pdf'})

def find_latest():
    r=SESSION.get(PAGE, timeout=30)
    r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser')
    reports=[]
    for anchor in soup.find_all('a',href=True):
        url=urljoin(PAGE,anchor['href'])
        m=PDF_RX.search(urlparse(url).path)
        if not m or urlparse(url).hostname != 'ak-static.cms.nba.com':
            continue
        date,hour,minute,ampm=m.groups()
        try:
            dt=datetime.strptime(f'{date} {hour}:{minute} {ampm.upper()}','%Y-%m-%d %I:%M %p')
        except ValueError:
            continue
        reports.append((dt,url))
    if not reports:
        raise RuntimeError('NBA sayfasinda PDF linki bulunamadi')
    dt,url=max(reports,key=lambda x:x[0])
    return dt,url

def normalize_player(last,first):
    # Maintain official spelling except for obvious suffix concatenations.
    last=re.sub(r'(Jr\.|Jr|Sr\.|Sr|II|III|IV)$',r' \1',last)
    return f'{first} {last}'.replace('  ',' ').strip()

def parse_pdf(raw):
    records=[]
    unsubmitted=[]
    team=None
    current=None
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            for raw_line in (page.extract_text() or '').splitlines():
                line=raw_line.strip()
                if not line or HEADER_RX.match(line):
                    continue
                # Team is only updated when a name exactly matching the official list appears.
                team_match=TEAM_RX.search(line)
                if team_match:
                    team=team_match.group(0)
                if 'NOTYETSUBMITTED' in line.replace(' ','').upper():
                    unsubmitted.append(team or 'UNKNOWN')
                    current=None
                    continue
                m=PLAYER_RX.search(line)
                if m:
                    if not team:
                        raise RuntimeError('Oyuncu icin takim bulunamadi: '+line)
                    current={
                        'player_name': normalize_player(m['last'],m['first']),
                        'team': team,
                        'status': m['status'].upper(),
                        'reason': line[m.end():].strip()[:500]
                    }
                    records.append(current)
                elif current and not team_match and not re.search(r'\b\d{2}:\d{2}\(ET\)',line):
                    # Continuation lines of injury reasons. Occasionally pdf text starts the reason
                    # on the preceding line; do not accidentally attach a new reason to someone else.
                    if line.startswith('Injury/Illness') or not PLAYER_RX.search(line):
                        current['reason']=(current['reason']+' '+line).strip()[:500]
    seen=set()
    for row in records:
        key=(row['team'],row['player_name'])
        if key in seen:
            raise RuntimeError('Tekrar eden oyuncu bulundu: '+str(key))
        seen.add(key)
    if not records:
        raise RuntimeError('PDF icinden oyuncu cikarilamadi')
    return records,sorted(set(unsubmitted))

def main():
    dt,url=find_latest()
    print('Secilen rapor:', url)
    response=SESSION.get(url, timeout=45)
    response.raise_for_status()
    if not response.content.startswith(b'%PDF-'):
        raise RuntimeError('PDF olmayan icerik alindi')
    records,missing=parse_pdf(response.content)
    data={
        'report_url':url,
        'report_key':dt.strftime('%Y-%m-%d_%H%M'),
        'report_date':dt.strftime('%Y-%m-%d %H:%M ET'),
        'players':records,
        'not_submitted_teams':missing
    }
    print('Oyuncular:',len(records),'Rapor gondermeyen takımlar:',len(missing))
    print('Durumlar:',{s:sum(x['status']==s for x in records) for s in sorted(set(x['status'] for x in records))})
    print('Ilk 5:',json.dumps(records[:5],ensure_ascii=False))
    # No secrets in logs.
    if not os.getenv('NBA_IMPORT_TOKEN'):
        raise RuntimeError('NBA_IMPORT_TOKEN GitHub secret eksik')
    worker=os.getenv('WORKER_URL','https://cizgi-masasi-api.k-melihsari.workers.dev').rstrip('/')
    if not worker.startswith('https://'):
        raise RuntimeError('HTTPS Worker adresi gerekli')
    result=SESSION.post(worker+'/api/import-nba',json=data,headers={
        'Authorization':'Bearer '+os.environ['NBA_IMPORT_TOKEN']
    },timeout=45)
