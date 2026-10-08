from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys,time,json,statistics,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from framework.client import Api,check,Db,product,stock,evidence
db=Db(); p=product(db); before=stock(db,p['id'])
def request(index):
    api=Api(); start=time.perf_counter()
    try:
        count=check(api.call('GET','/wx/goods/count'))
        assert count>0
        return {'request':index,'milliseconds':(time.perf_counter()-start)*1000,'passed':True}
    finally: api.close()
started=time.perf_counter()
with ThreadPoolExecutor(max_workers=5) as pool: rows=list(pool.map(request,range(50)))
elapsed=time.perf_counter()-started; times=sorted(r['milliseconds'] for r in rows)
assert stock(db,p['id'])==before
data={'scope':'Local read-only smoke, NOT a capacity benchmark or JMeter test','threads':5,'requests':50,
    'passed':len(rows),'failed':0,'elapsed_seconds':elapsed,'median_ms':statistics.median(times),
    'p95_ms':times[int(len(times)*.95)-1],'stock_unchanged':True,'raw_samples':rows}
folder=Path(os.environ['EVIDENCE_DIR']); folder.mkdir(parents=True,exist_ok=True)
(folder/'summary.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in data.items() if k!='raw_samples'},ensure_ascii=False)); db.close()
