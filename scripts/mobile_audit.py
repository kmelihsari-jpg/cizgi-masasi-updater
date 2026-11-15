#!/usr/bin/env python3
"""Cizgi Masasi mobile UI smoke test; read-only live site checks."""
import json, os, pathlib, time
from playwright.sync_api import sync_playwright

URL = os.environ.get('CM_URL', 'https://cizgi-masasi.pages.dev/')
OUT = pathlib.Path(os.environ.get('CM_AUDIT_OUT', 'mobile-audit-results'))
OUT.mkdir(parents=True, exist_ok=True)
SIZES = [(320, 700), (360, 780), (390, 844), (430, 932), (768, 1024)]
reports = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    for width, height in SIZES:
        ctx = browser.new_context(viewport={'width': width, 'height': height},
                                  device_scale_factor=1,
                                  is_mobile=width < 700, has_touch=width < 700,
                                  locale='tr-TR', timezone_id='Europe/Istanbul',
                                  reduced_motion='reduce')
        page = ctx.new_page()
        js_errors = []
        page.on('pageerror', lambda exc: js_errors.append(str(exc)))
        result = {'size': f'{width}x{height}', 'url': URL}
        try:
            response = page.goto(URL, wait_until='domcontentloaded', timeout=45000)
            result['http_status'] = response.status if response else None
            page.wait_for_timeout(5000)
            page.screenshot(path=str(OUT / f'ana-{width}.png'), full_page=False, animations='disabled')
            info = page.evaluate('''() => {
                const v = document.documentElement.clientWidth;
                const rect = el => el.getBoundingClientRect();
                const nav = document.querySelector('#bnav');
                const vitrin = document.querySelector('#cm-v1-vitrin');
                const grid = document.querySelector('.cmv-grid');
                const overflow = [...document.querySelectorAll('body *')]
                  .filter(el => {
                    const s = getComputedStyle(el), r = rect(el);
                    if (s.display === 'none' || s.visibility === 'hidden' || s.position === 'fixed' || s.position === 'absolute') return false;
                    if (r.width < 2 || r.height < 2 || !r.right) return false;
                    return r.right > v + 4 || r.left < -4;
                  }).slice(0, 18).map(el => ({
                    tag: el.tagName.toLowerCase(),
                    id: el.id, className: typeof el.className==='string'?el.className.slice(0,65):'',
                    right: Math.round(rect(el).right), left: Math.round(rect(el).left),
                    text: (el.innerText || '').slice(0,40)
                  }));
                return {
                    viewport: v, documentWidth: document.documentElement.scrollWidth,
                    hasMobileNav: !!nav && getComputedStyle(nav).display !== 'none',
                    hasVitrin: !!vitrin && getComputedStyle(vitrin).display !== 'none',
                    vitrinCardCount: grid ? grid.children.length : 0,
                    vitrinColumnCount: grid ? getComputedStyle(grid).gridTemplateColumns.split(' ').filter(Boolean).length : null,
                    overflow
                };
            }''')
            result.update(info)
            result['horizontal_page_overflow'] = info['documentWidth'] > info['viewport'] + 4
            if width <= 430:
                result['mobile_nav_ok'] = info['hasMobileNav']
                result['vitrin_grid_ok'] = info['vitrinColumnCount'] == 2 if info['hasVitrin'] else True
                # Exercise mobile more menu and capture its layout.
                more = page.locator('#bnav button[data-bv="more"]')
                if more.count() and more.is_visible():
                    more.click(timeout=6000)
                    page.wait_for_timeout(250)
                    result['more_menu_visible'] = page.locator('#bsheet').is_visible()
                    page.screenshot(path=str(OUT / f'menu-{width}.png'), full_page=False, animations='disabled')
            result['mobile_tools_ok'] = True
            if width <= 430:
                tools = page.locator('#view-home details.cm-mobile-tools')
                result['mobile_tools_ok'] = tools.count() == 1 and tools.locator('summary').is_visible()
                if tools.count():
                    tools.locator('summary').click(timeout=6000)
                    result['mobile_tools_open'] = page.locator('#inj-up').is_visible()
                    page.screenshot(path=str(OUT / f'kontroller-{width}.png'), full_page=False, animations='disabled')
            result['page_errors'] = js_errors[:8]
        except Exception as exc:
            result['error'] = str(exc)[:350]
        reports.append(result)
        print(json.dumps(result, ensure_ascii=False))
        ctx.close()
    browser.close()
(OUT / 'report.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
with (OUT / 'report.md').open('w', encoding='utf-8') as f:
    f.write('# Çizgi Masası mobil ekran testi\n\n')
    for r in reports:
        f.write(f"## {r['size']}\n\n")
        f.write(f"HTTP: {r.get('http_status','?')} · Sayfa genişliği: {r.get('documentWidth','?')} · Ekran: {r.get('viewport','?')} · Yatay taşma: {r.get('horizontal_page_overflow','?')}\n\n")
        f.write(f"Mobil menü: {r.get('mobile_nav_ok','?')} · Vitrin: {r.get('hasVitrin','?')} · Vitrin sütunu: {r.get('vitrinColumnCount','?')} · Daha fazla menüsü: {r.get('more_menu_visible','?')}\n\n")
        if r.get('overflow'): f.write('Taşan öğeler: `'+json.dumps(r['overflow'],ensure_ascii=False)+'`\n\n')
        if r.get('error'): f.write('Hata: '+r['error']+'\n\n')
        if r.get('page_errors'): f.write('JS hataları: `'+str(r['page_errors'])+'`\n\n')
failures=[r for r in reports if r.get('error') or (r.get('http_status') or 0)>=400 or r.get('horizontal_page_overflow') or (int(r['size'].split('x')[0]) <= 430 and (not r.get('mobile_nav_ok') or not r.get('vitrin_grid_ok') or not r.get('more_menu_visible') or not r.get('mobile_tools_ok') or not r.get('mobile_tools_open')))]
print(f'MOBILE AUDIT: {len(reports)} ekran, {len(failures)} kritik sorun')
raise SystemExit(1 if failures else 0)
