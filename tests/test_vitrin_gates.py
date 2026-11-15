import ast
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts'/'karne_automation.py'
s=p.read_text(encoding='utf-8')
ast.parse(s)
assert 'age>0.6' in s and 'age>6' not in s
assert "typeof LIVE!=='undefined'" in s
assert 'Date.now()-Number(LIVE.ts)<=3*3600*1000' in s
assert 'if not out:' in s
assert "old_by_day={d.get('date'):d for d in docs}" in s
assert 'page.route' in s
print('PASS: Vitrin freshness + injury gates, syntax, existing karne preservation checks')
