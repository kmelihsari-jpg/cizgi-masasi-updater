#!/usr/bin/env python3
"""Hashtag Basketball rotation-trends -> rotation.json (Cizgi Masasi).

Sekil: {src, season, updated, t:{TAKIM:{g, d, p:[{n, gp, st, mn, b[48], q4, fe, fn, l5, lg}]}}}
Hesap, 11 Kasim'da tarayicida kullanilan JS ile birebir ayni (tek fark: uzatma
stintlerinde q4 artik negatif eklenmez). Bir takim cekilemezse --prev dosyasindaki
eski kaydi korunur.
"""
import argparse
import http.cookiejar
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from html.parser import HTMLParser
from math import floor

URL = 'https://hashtagbasketball.com/rotation-trends'
TEAM_FIELD = 'ctl00$ContentPlaceHolder1$DDTEAM'
TEAM_MAP = {'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'PHO': 'PHX', 'SA': 'SAS'}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/131.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9',
}
RT_RE = re.compile(r'<script[^>]*id="rt-data"[^>]*>([\s\S]*?)</script>')


def jround(x):  # JS Math.round
    return int(floor(x + 0.5))


def fix1(x):  # JS +x.toFixed(1)
    v = float(Decimal(x).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
    return int(v) if v.is_integer() else v


def compute(j):
    ng = len(j['games'])
    per = [{'g': {}, 'st': set(), 'q4': 0.0, 'long': []} for _ in j['players']]
    by_gp = {}
    for s in j['stints']:
        pi, gi, a, b = s[0], s[1], s[2], s[3]
        st = s[5] if len(s) > 5 else 0
        P = per[pi]
        P['g'].setdefault(gi, None)  # ekleme sirasi korunur (JS Set gibi)
        if st:
            P['st'].add(gi)
        e = min(b, 2880)
        for m in range(48):
            lo, hi = m * 60, m * 60 + 60
            ov = max(0, min(e, hi) - max(a, lo))
            if ov > 0:
                arr = by_gp.setdefault(pi, {}).setdefault(gi, [0.0] * 48)
                arr[m] += ov / 60
        if e > 2160:
            P['q4'] += max(0, min(e, 2880) - max(a, 2160))
        P['long'].append(b - a)
    res = []
    for pi, p in enumerate(j['players']):
        P = per[pi]
        gp = len(P['g'])
        if not gp:
            continue
        gm = by_gp.get(pi, {})
        bins = [0.0] * 48
        for gi in sorted(gm):  # JS: sayisal anahtarlar artan sirada
            for m, v in enumerate(gm[gi]):
                bins[m] += min(1, v)
        fe = []
        for gi in P['g']:
            if gi in P['st']:
                continue
            starts = [s[2] for s in j['stints'] if s[0] == pi and s[1] == gi]
            if starts:
                fe.append(min(starts))
        mins = 0.0
        for gi in sorted(gm):  # JS: once her mac kendi icinde toplanir
            sub = 0.0
            for v in gm[gi]:
                sub += v
            mins += sub
        q4last = sum(1 for gi in P['g'] if any(v >= .5 for v in gm.get(gi, [0.0] * 48)[43:48]))
        top = sorted(P['long'], reverse=True)[:3]
        res.append({
            'n': p['name'], 'gp': gp, 'st': len(P['st']),
            'mn': fix1(mins / gp),
            'b': [jround(v / gp * 100) for v in bins],
            'q4': fix1(P['q4'] / 60 / gp),
            'fe': jround(sum(fe) / len(fe)) if fe else None,
            'fn': len(fe),
            'l5': jround(q4last / gp * 100),
            'lg': fix1((sum(top) / 60) / (len(top) or 1)),
        })
    return {'g': ng, 'd': j['games'][-1]['date'] if ng else None, 'p': res}


class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields, self.sel, self.opts, self.season = {}, None, {}, None
        self._first = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'input' and a.get('name') and a.get('type', 'text') in ('hidden', 'text'):
            self.fields[a['name']] = a.get('value') or ''
        elif tag == 'select' and a.get('name'):
            self.sel = a['name']
            self.opts[self.sel] = []
        elif tag == 'option' and self.sel:
            v = a.get('value', '')
            self.opts[self.sel].append(v)
            self._first.setdefault(self.sel, v)
            if 'selected' in a:
                self.fields[self.sel] = v
                self._cur_sel = True
            else:
                self._cur_sel = False

    def handle_data(self, data):
        if self.sel and self.sel.endswith('DDSEASON') and getattr(self, '_cur_sel', False) and data.strip():
            self.season = data.strip()
            self._cur_sel = False

    def handle_endtag(self, tag):
        if tag == 'select':
            if self.sel not in self.fields and self._first.get(self.sel) is not None:
                self.fields[self.sel] = self._first[self.sel]
            self.sel = None


def fetch(opener, data=None, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(URL, data=data, headers={**HEADERS, 'Referer': URL})
            if data is not None:
                req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            with opener.open(req, timeout=40) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f'istek basarisiz: {last}')


def rt_json(html):
    m = RT_RE.search(html)
    if not m:
        raise RuntimeError('rt-data bulunamadi')
    return json.loads(m.group(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='out/rotation.json')
    ap.add_argument('--prev', default='seed/rotation.json')
    ap.add_argument('--min-teams', type=int, default=28)
    ap.add_argument('--delay', type=float, default=1.0)
    args = ap.parse_args()

    prev = {}
    try:
        with open(args.prev, encoding='utf-8') as f:
            prev = json.load(f).get('t', {})
    except Exception:  # noqa: BLE001
        pass

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    html = fetch(opener)
    fp = FormParser()
    fp.feed(html)
    codes = fp.opts.get(TEAM_FIELD) or []
    if len(codes) < 28:
        raise SystemExit(f'Takim listesi okunamadi ({len(codes)})')
    base = dict(fp.fields)
    first = rt_json(html)

    out, err = {}, []
    for code in codes:
        name = TEAM_MAP.get(code, code)
        try:
            if code == first.get('team'):
                j = first
            else:
                time.sleep(args.delay)
                form = dict(base)
                form.update({TEAM_FIELD: code, '__EVENTTARGET': TEAM_FIELD, '__EVENTARGUMENT': ''})
                j = rt_json(fetch(opener, urllib.parse.urlencode(form).encode()))
                if j.get('team') not in (code, name):
                    raise RuntimeError(f"yanlis takim dondu: {j.get('team')}")
            out[name] = compute(j)
        except Exception as e:  # noqa: BLE001
            err.append(f'{code}: {e}')
            if name in prev:
                out[name] = prev[name]
                print(f'::warning::{code} cekilemedi, eski kayit korundu: {e}')
            else:
                print(f'::warning::{code} cekilemedi: {e}')

    fresh = len(codes) - len(err)
    print(f'Rotasyon: {fresh}/{len(codes)} takim taze, {len(out)} takim dosyada')
    if fresh < args.min_teams:
        raise SystemExit(f'Yetersiz taze takim: {fresh}')
    dates = [t['d'] for t in out.values() if t.get('d')]
    doc = {'src': 'hashtagbasketball.com/rotation-trends', 'season': fp.season or '',
           'updated': max(dates) if dates else '', 't': out}
    import os
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(doc, f, separators=(',', ':'), ensure_ascii=False)
    print('Yazildi:', args.out, doc['updated'])


if __name__ == '__main__':
    sys.exit(main())
