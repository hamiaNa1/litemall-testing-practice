from pathlib import Path
from dotenv import dotenv_values
import pymysql
root=Path(__file__).resolve().parents[1]; c=dotenv_values(root/'.env')
try:
    db=pymysql.connect(host='127.0.0.1',port=13306,user='root',password=c['DB_ROOT_PASSWORD'],autocommit=True)
except pymysql.err.OperationalError as error:
    if error.args[0]==2003: print('Private MySQL already stopped'); raise SystemExit(0)
    raise
with db.cursor() as cur:
    cur.execute('SELECT @@datadir')
    assert Path(cur.fetchone()[0]).resolve()==(root/'.runtime/mysql-data').resolve()
    cur.execute('SHUTDOWN')
print('Private MySQL gracefully stopped')
