#!/usr/bin/env python3
"""Inspect public CourtSketch first-party JavaScript for documented-looking data routes.
Read-only: fetches HTML/linked same-origin JS, does not call discovered APIs.
"""
from html.parser import HTMLParser
import json
import re
import urllib.error
import urllib.parse
import urllib.request

ROOT = 'https://courtsketch.com'
PAGES = ('/statboard', '/game-finder')
MAX_SCRIPT_COUNT = 24
MAX_SCRIPT_BYTES = 2_000_000
MAX_TOTAL_BYTES = 12_000_000
HEADERS = {'User-Agent':'Mozilla/5.0 (compatible; source-evaluation/1.0)', 'Accept':'text/html,application/javascript,*/*'}

class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            src = dict(attrs).get('src')
            if src: self.scripts.append(src)

def get(url, limit):
    req=urllib.request.Request(url,headers=HEADERS)
    try:
        with urllib.request.urlopen(req,timeout=18) as response:
            if response.url.split('/')[2] != 'courtsketch.com':
                return None, 'redirected outside courtsketch.com'
            b=response.read(limit+1)
            if len(b)>limit:return None, 'over byte limit'
            return b.decode('utf-8','replace'),None
    except urllib.error.HTTPError as e:
        return None, 'HTTP %d' % e.code
    except Exception as e:
        return None, type(e).__name__ + ': ' + str(e)[:90]

def route_hits(js):
    # Extract candidate literals; intentionally do not execute JS or request endpoints.
    patterns = [
        r'(?<![\w])(?:/api|/v1|/v2|/graphql|/_next/data)/[a-zA-Z0-9_/$?&=.%{}:/-]{2,130}',
        r'https?://[a-zA-Z0-9.-]+/(?:api|v1|v2|graphql)/[a-zA-Z0-9_/$?&=.%{}:/-]{2,130}',
    ]
    hits=[]
    for pat in patterns:
        hits.extend(re.findall(pat, js))
    # Remove sensitive query values and keep path-only route hints.
    cleaned=[]
    for v in hits:
        v=v.split('?')[0].split('#')[0]
        if re.search(r'(tracking|stat|player|game|leader|finder|board|search|export|download|query|graphql)', v, re.I):
            cleaned.append(v[:150])
    return sorted(set(cleaned))[:35]

def main():
    urls=[]; pages=[]
    for path in PAGES:
        page,err=get(ROOT+path,1_500_000)
        if err:
            pages.append({'path':path,'error':err}); continue
        parser=ScriptParser();parser.feed(page)
        pages.append({'path':path,'scripts_linked':len(parser.scripts)})
        for src in parser.scripts:
            url=urllib.parse.urljoin(ROOT+path,src)
            parsed=urllib.parse.urlparse(url)
            if parsed.scheme=='https' and parsed.netloc=='courtsketch.com' and (parsed.path.endswith('.js') or '/_next/' in parsed.path):
                if url not in urls:urls.append(url)
    outcomes=[]; total=0
    for url in urls[:MAX_SCRIPT_COUNT]:
        if total >= MAX_TOTAL_BYTES:break
        budget=min(MAX_SCRIPT_BYTES,MAX_TOTAL_BYTES-total)
        js,err=get(url,budget)
        record={'script_path':urllib.parse.urlparse(url).path[:200]}
        if err:
            record['error']=err
        else:
            total += len(js.encode('utf-8', 'replace'))
            record.update({'length':len(js),'mentions_potential_assists':bool(re.search('potential.?assist|POTENTIAL_AST',js,re.I)),
                           'mentions_rebound_chances':bool(re.search('reb(?:ound)?_?chances?|REB_CHANCES',js,re.I)),
                           'data_route_hints':route_hits(js)})
        outcomes.append(record)
    output={'pages':pages,'script_count_found':len(urls),'script_count_checked':len(outcomes),
            'max_total_bytes':MAX_TOTAL_BYTES,'scripts':outcomes}
    print(json.dumps(output,ensure_ascii=False,indent=2))
    matches=[x for x in outcomes if x.get('data_route_hints')]
    print('VERDICT:', 'PUBLIC_JS_ROUTE_HINTS_FOUND (not verified data access)' if matches else 'NO_CLEAR_PUBLIC_DATA_ROUTES_FOUND')
    print('READ ONLY: endpoints are not requested; no repository or website data modified')

if __name__=='__main__':main()
