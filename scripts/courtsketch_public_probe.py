#!/usr/bin/env python3
"""Read-only check of publicly linked CourtSketch data/export resources.
Does not scrape tables, bypass access restrictions, or alter repository data.
"""
import html.parser
import json
import re
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://courtsketch.com'
PAGES = ['/statboard', '/game-finder']
HEADERS = {'User-Agent': 'CizgiMasasi-DataSourceEvaluation/1.0 (read-only; public pages)', 'Accept': 'text/html,application/xhtml+xml'}
MAX_BYTES = 1200000

class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        if tag == 'script' and a.get('src'):
            self.scripts.append(a['src'])

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=16) as resp:
            raw = resp.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                return {'status': resp.status, 'error': 'response larger than safety cap'}
            return {'status': resp.status, 'html': raw.decode('utf-8', 'replace'), 'type': resp.headers.get('content-type', '')}
    except urllib.error.HTTPError as exc:
        return {'status': exc.code, 'error': 'HTTP error'}
    except Exception as exc:
        return {'error': '%s: %s' % (type(exc).__name__, str(exc)[:160])}

def main():
    result = []
    for path in PAGES:
        url = BASE + path
        res = fetch(url)
        body = res.pop('html', '')
        links = Links()
        links.feed(body)
        candidates = []
        for item in links.links:
            absolute = urllib.parse.urljoin(url, item)
            if re.search(r'(\.csv(?:\?|$)|\.json(?:\?|$)|download|export|openapi)', absolute, re.I):
                candidates.append(absolute.split('?')[0][:200])
        rec = {
            'page': url,
            **res,
            'potential_assists_mentioned': bool(re.search(r'potential assist', body, re.I)),
            'rebound_chances_mentioned': bool(re.search(r'rebound chances?', body, re.I)),
            'contested_mentioned': bool(re.search(r'contested', body, re.I)),
            'public_export_links': sorted(set(candidates))[:20],
            'script_count': len(links.scripts),
        }
        result.append(rec)
    print(json.dumps({'results': result}, ensure_ascii=False, indent=2))
    print('VERDICT: Page reachability and exposed links only; game-level JSON/CSV not proven.')
    print('READ ONLY: No Git, seed, Cloudflare or tracking files modified.')

if __name__ == '__main__':
    main()
