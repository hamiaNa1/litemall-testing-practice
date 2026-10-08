from pathlib import Path
import sys,json,bcrypt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from framework.client import Db,config,ROOT
db=Db(); c=config()
for prefix in ['TEST','OTHER']:
    db.execute('UPDATE litemall_user SET password=%s WHERE username=%s',
        (bcrypt.hashpw(c[prefix+'_PASSWORD'].encode(),bcrypt.gensalt(prefix=b'2a')).decode(),c[prefix+'_USERNAME']))
for line in (ROOT/'evidence/p0/http.jsonl').read_text(encoding='utf-8').splitlines():
    row=json.loads(line)
    if row['path']=='/wx/auth/login' and row['response']['errno']==700 and row['request'].get('username','').startswith('qa_run_'):
        db.execute('DELETE FROM litemall_user WHERE username=%s',(row['request']['username'],))
db.close()
print('Project-owned seed hashes corrected to 2a; failed setup account cleaned')
