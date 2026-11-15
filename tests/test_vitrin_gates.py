import ast
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts'/'karne_automation.py'
s=p.read_text(encoding='utf-8')
ast.parse(s)
assert 'age>1.25' in s and 'age>6' not in s and 'age>0.6' not in s
assert 'def worker_sakatlik_taze' in s and 'worker_sakatlik_taze()' in s
assert 'window.CMREMOTE' in s and "typeof LIVE!=='undefined'" not in s
assert 'if not out:' in s
assert "old_by_day={d.get('date'):d for d in docs}" in s
assert 'page.route' in s
w=Path(__file__).resolve().parents[1]/'.github'/'workflows'/'cizgi-masasi-otomatik-pages.yml'
y=w.read_text(encoding='utf-8')
assert "github.event_name == 'push'" in y and "'site-patches/**'" in y
print('PASS: Karne kapisi V2 (Worker sakatlik tazeligi, 75 dk barem), push yayin tetikleyicisi')
