from pathlib import Path
import sys,os,subprocess,json,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from framework.client import ROOT,config,Db,stock
c=config()
binary=Path(os.environ.get('MYSQL_BIN','D:/DevTools/MySQL/mysql-8.4.11-winx64/bin'))/'mysql.exe'
sql=(ROOT/'sql/verify_business.sql').read_bytes()
result=subprocess.run([str(binary),'--no-defaults','-h127.0.0.1','-P13306','-u'+c['DB_USER'],'--default-character-set=utf8mb4','--batch','litemall_qa'],
    input=sql,capture_output=True,env=dict(os.environ,MYSQL_PWD=c['DB_PASSWORD']))
out=Path(os.environ.get('EVIDENCE_DIR',str(ROOT/'evidence/sql-script'))); out.mkdir(parents=True,exist_ok=True)
(out/'execution.tsv').write_bytes(result.stdout+result.stderr)
result.check_returncode()
db=Db(); remaining=db.query('SELECT COUNT(*) AS n FROM litemall_user WHERE LEFT(username,7)=%s',('qa_run_',))[0]['n']
assert stock(db,1)==100 and remaining==0, 'Run this cleanup check outside active write tests'
data={'sql_file_executed':'sql/verify_business.sql','mysql_exit':result.returncode,'remaining_fixture_users':remaining,'product_1_stock':100,
    'note':'Default order/cart IDs are 0; previous fixture orders were cleaned. Use saved SQL snapshots for those orders.'}
(out/'summary.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(data,ensure_ascii=False)); db.close()
