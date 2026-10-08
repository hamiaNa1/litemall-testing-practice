from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import os, json, uuid, logging
import requests, pymysql, bcrypt, allure
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]

def config():
    c = {**dotenv_values(ROOT/'.env'), **os.environ}
    assert c['DB_HOST'] == '127.0.0.1' and c['DB_NAME'] == 'litemall_qa' and int(c['DB_PORT']) == 13306, 'Only the isolated local database on port 13306 is allowed'
    assert c['BASE_URL'].startswith('http://127.0.0.1:'), 'Only the local SUT is allowed'
    return c

def redact(value):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if any(s in k.lower() for s in ['password','token','secret','authorization','cookie','sessionkey']) else redact(v) for k,v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        for k,v in dotenv_values(ROOT/'.env').items():
            if v and any(s in k for s in ['PASSWORD','SECRET']):
                value = value.replace(v, '[REDACTED]')
    return value

def evidence(name, value):
    folder = Path(os.environ.get('EVIDENCE_DIR', str(ROOT/'evidence/current')))
    folder.mkdir(parents=True, exist_ok=True)
    safe = redact(value)
    with (folder/(name+'.jsonl')).open('a', encoding='utf-8') as f:
        f.write(json.dumps({'time':datetime.now(timezone.utc).isoformat(), **safe}, ensure_ascii=False, default=str)+'\n')
    allure.attach(json.dumps(safe, ensure_ascii=False, indent=2, default=str), name=name, attachment_type=allure.attachment_type.JSON)

class Api:
    def __init__(self, token=None):
        self.session = requests.Session()
        self.session.trust_env = False
        self.base = config()['BASE_URL']
        if token:
            self.session.headers['X-Litemall-Token'] = token

    def call(self, method, path, *, body=None, params=None, raw=None):
        response = self.session.request(method, self.base+path, json=body, params=params,
            data=raw, headers={'Content-Type':'application/json'} if raw is not None else None, timeout=(3,15))
        try:
            data = response.json()
        except ValueError:
            data = {'non_json':response.text[:1000]}
        evidence('http', {'method':method,'path':path,'request':body if raw is None else raw,
            'params':params,'http_status':response.status_code,'response':data})
        logging.info('%s %s HTTP=%s errno=%s', method,path,response.status_code,data.get('errno'))
        return response

    def close(self):
        self.session.close()

def check(response, errno=0, http=200):
    assert response.status_code == http, f'HTTP expected {http}, actual {response.status_code}'
    data = response.json()
    assert isinstance(data, dict) and isinstance(data.get('errno'), int), 'Missing integer errno'
    assert isinstance(data.get('errmsg'), str), 'Missing errmsg'
    assert data['errno'] == errno, f'Business errno expected {errno}, actual {data["errno"]}: {data["errmsg"]}'
    return data.get('data')

class Db:
    def __init__(self):
        c = config()
        self.conn = pymysql.connect(host=c['DB_HOST'],port=int(c['DB_PORT']),user=c['DB_USER'],
            password=c['DB_PASSWORD'],database=c['DB_NAME'],charset='utf8mb4',autocommit=True,
            cursorclass=pymysql.cursors.DictCursor)

    def query(self, sql, args=()):
        assert sql.lstrip().upper().startswith('SELECT'), 'query is read-only'
        with self.conn.cursor() as cur:
            cur.execute(sql,args)
            rows = cur.fetchall()
        evidence('sql', {'sql':sql,'parameters':args,'rows':rows})
        return rows

    def execute(self, sql, args=()):
        with self.conn.cursor() as cur:
            cur.execute(sql,args)
            return cur.lastrowid

    def close(self):
        self.conn.close()

@dataclass(repr=False)
class Actor:
    db: Db
    username: str
    id: int
    api: Api = field(repr=False)

    @classmethod
    def create(cls, db):
        c = config()
        username = 'qa_run_'+uuid.uuid4().hex[:16]
        encoded = bcrypt.hashpw(c['TEST_PASSWORD'].encode(),bcrypt.gensalt(prefix=b'2a')).decode()
        uid = db.execute('INSERT INTO litemall_user (username,password,nickname,add_time,update_time,deleted) VALUES (%s,%s,%s,NOW(),NOW(),0)', (username,encoded,username))
        api = Api()
        try:
            login = check(api.call('POST','/wx/auth/login',body={'username':username,'password':c['TEST_PASSWORD']}))
        except Exception:
            api.close()
            db.execute('DELETE FROM litemall_user WHERE id=%s AND username=%s',(uid,username))
            raise
        assert login['userInfo']['nickName'] == username and isinstance(login['token'],str) and len(login['token']) > 10
        api.session.headers['X-Litemall-Token'] = login['token']
        return cls(db,username,uid,api)

    def address(self):
        body = {'id':0,'name':'QA 测试','tel':'13800138000','province':'广东省','city':'深圳市',
            'county':'南山区','areaCode':'440305','addressDetail':'仅测试不发货 QA','isDefault':True}
        aid = check(self.api.call('POST','/wx/address/save',body=body))
        assert isinstance(aid,int) and aid > 0
        return aid

    def cart(self, product, number=1):
        cid = check(self.api.call('POST','/wx/cart/fastadd',body={'goodsId':product['goods_id'],'productId':product['id'],'number':number}))
        assert isinstance(cid,int) and cid > 0
        return cid

    def submit(self, cart_id, address_id):
        return self.api.call('POST','/wx/order/submit',body={'cartId':cart_id,'addressId':address_id,'couponId':0,
            'userCouponId':0,'grouponRulesId':0,'grouponLinkId':0,'message':'QA 独立测试订单，无真实支付'})

    def cleanup(self):
        assert self.username.startswith('qa_run_'), 'Only fixture-created accounts may be cleaned'
        rows = self.db.query('SELECT id,order_status FROM litemall_order WHERE user_id=%s',(self.id,))
        for order in rows:
            if order['order_status'] == 101:
                check(self.api.call('POST','/wx/order/cancel',body={'orderId':order['id']}))
            self.db.execute('DELETE FROM litemall_order_goods WHERE order_id=%s',(order['id'],))
        # Deletes are scoped to an account generated by this fixture, never seed/customer data.
        assert self.username.startswith('qa_run_')
        for table in ['litemall_order','litemall_cart','litemall_address','litemall_coupon_user','litemall_search_history','litemall_footprint']:
            self.db.execute(f'DELETE FROM {table} WHERE user_id=%s',(self.id,))
        self.db.execute('DELETE FROM litemall_user WHERE id=%s AND username=%s',(self.id,self.username))
        assert not self.db.query('SELECT id FROM litemall_user WHERE id=%s',(self.id,))
        evidence('cleanup', {'user_id':self.id,'username':self.username,'order_ids':[r['id'] for r in rows],'status':'completed'})
        self.api.close()

def product(db):
    rows = db.query('SELECT p.id,p.goods_id,p.number,p.price,p.specifications,g.name FROM litemall_goods_product p JOIN litemall_goods g ON g.id=p.goods_id WHERE p.deleted=0 AND g.deleted=0 AND g.is_on_sale=1 AND p.number>=5 ORDER BY p.id LIMIT 1')
    assert rows, 'No purchasable seed product'
    return rows[0]

def stock(db,pid):
    return db.query('SELECT id,number FROM litemall_goods_product WHERE id=%s',(pid,))[0]['number']

def order_row(db,oid):
    rows = db.query('SELECT id,user_id,order_status,goods_price,freight_price,actual_price FROM litemall_order WHERE id=%s',(oid,))
    assert len(rows)==1
    return rows[0]
