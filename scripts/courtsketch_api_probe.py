#!/usr/bin/env python3
"""Read-only, low-volume inspection of two publicly linked CourtSketch routes.
No auth, no data writes, and no crawling of player data.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

BASE = 'https://courtsketch.com'
HEADERS = {'User-Agent': 'CizgiMasasiResearch/1.0 (public-source-compatibility-check)', 'Accept': 'application/json,text/plain,*/*'}
PATHS = ['/api/game_finder/players', '/api/game_finder']
JS_PATH = '/static/js/game_finder.js'


def get(path, max_bytes=65536):
    request = urllib.request.Request(BASE + path, headers=HEADERS, method='GET')
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            raw = response.read(max_bytes + 1)
            return response.status, response.headers.get('Content-Type', ''), raw[:max_bytes], len(raw) > max_bytes
    except urllib.error.HTTPError as error:
        raw = error.read(min(max_bytes, 4096))
        return error.code, error.headers.get('Content-Type', ''), raw, False
    except Exception as error:
        return None, '', (type(error).__name__ + ': ' + str(error)).encode(), False


def sample_body(data, content_type):
    content = data.decode('utf-8', 'replace')
    if 'json' in content_type.lower():
        try:
            result = json.loads(content)
            if isinstance(result, dict):
                keys = list(result)[:18]
                types = {key: type(result[key]).__name__ for key in keys}
                lens = {key: len(result[key]) for key in keys if isinstance(result[key], (dict, list))}
                return {'shape': 'object', 'keys': keys, 'types': types, 'sizes': lens}
            if isinstance(result, list):
                sample = result[0] if result else None
                return {'shape': 'array', 'count': len(result), 'sample_item_type': type(sample).__name__, 'sample_item_keys': list(sample)[:18] if isinstance(sample, dict) else []}
            return {'shape': type(result).__name__}
        except (ValueError, TypeError):
            pass
    # Do not output entire HTML pages, potential user content, or arbitrary data values.
    return {'body_prefix': re.sub(r'\s+', ' ', content[:240])}


def main():
    status, typ, data, _ = get('/robots.txt', 16000)
    robot = urllib.robotparser.RobotFileParser()
    if status == 200:
        robot.parse(data.decode('utf-8', 'replace').splitlines())
    print('ROBOTS', json.dumps({'http_status': status, 'robots_read': status == 200}, ensure_ascii=False))
    js_allowed = status != 200 or robot.can_fetch(HEADERS['User-Agent'], BASE + JS_PATH)
    if js_allowed:
        js_status, js_type, js_data, truncated = get(JS_PATH, 100000)
        js = js_data.decode('utf-8', 'replace')
        contexts = []
        for path in PATHS:
            match = re.search(re.escape(path), js)
            if match:
                context = re.sub(r'\s+', ' ', js[max(0, match.start() - 170): match.end() + 230])
                contexts.append({'endpoint': path, 'js_context': context})
        print('JS', json.dumps({'status': js_status, 'type': js_type, 'truncated': truncated, 'route_context': contexts}, ensure_ascii=False))
    for path in PATHS:
        if status == 200 and not robot.can_fetch(HEADERS['User-Agent'], BASE + path):
            print('API', json.dumps({'path': path, 'skipped': 'robots disallow'}, ensure_ascii=False))
            continue
        code, mime, raw, truncated = get(path, 24000)
        print('API', json.dumps({'path': path, 'status': code, 'content_type': mime, 'truncated': truncated, 'response': sample_body(raw, mime)}, ensure_ascii=False))
    print('READ ONLY: 2 API checks maximum; no seed, tracking, Git, or Pages changes')


if __name__ == '__main__':
    main()
