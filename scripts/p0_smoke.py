"""First batch: real business execution before the pytest suite is implemented."""
import sys, json, traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from framework.client import Api,Db,Actor,check,product,stock,order_row,evidence,ROOT

db=Db(); guest=Api(); actor=None; results=[]
def case(cid,title,fn):
    try:
        fn(); status='passed'; detail='All assertions passed'
    except Exception as e:
        status='failed'; detail=str(e); traceback.print_exc()
    results.append({'id':cid,'title':title,'status':status,'detail':detail})
    print(cid,status,title)

def equal(actual,expected):
    assert actual==expected, f'Expected {expected}, actual {actual}'

try:
    p=product(db); baseline=stock(db,p['id'])
    case('F001','商品总数可查询',lambda: equal(check(guest.call('GET','/wx/goods/count'))>0,True))
    case('F002','商品详情关联库存货品',lambda: equal(check(guest.call('GET','/wx/goods/detail',params={'id':p['goods_id']}))['info']['id'],p['goods_id']))
    case('F003','缺少登录参数被拒绝',lambda: check(guest.call('POST','/wx/auth/login',body={}),401))
    case('F004','不存在账号登录失败',lambda: check(guest.call('POST','/wx/auth/login',body={'username':'qa_does_not_exist','password':'invalid'}),700))
    case('F005','无 Token 不可查询购物车',lambda: check(guest.call('GET','/wx/cart/index'),501))
    case('F006','无效 Token 不可查询订单',lambda: check(Api('invalid-token').call('GET','/wx/order/list'),501))
    case('F007','注册必填校验',lambda: check(guest.call('POST','/wx/auth/register',body={}),401))
    case('F008','短信验证码服务未启用',lambda: check(guest.call('POST','/wx/auth/regCaptcha',body={'mobile':'13800138000'}),701))
    actor=Actor.create(db)
    case('F009','真实账号登录及 Token 提取',lambda: equal(check(actor.api.call('GET','/wx/cart/index'))['cartList'],[]))
    case('F010','购物车数量零被拒绝',lambda: check(actor.api.call('POST','/wx/cart/add',body={'goodsId':p['goods_id'],'productId':p['id'],'number':0}),401))
    aid=actor.address(); cid=actor.cart(p,2)
    case('F011','加入购物车不扣减库存',lambda: equal(stock(db,p['id']),baseline))
    case('F012','购物车 SQL 数量正确',lambda: equal(db.query('SELECT number FROM litemall_cart WHERE id=%s AND user_id=%s',(cid,actor.id))[0]['number'],2))
    oid=check(actor.submit(cid,aid))['orderId']
    case('F013','下单生成待付款订单',lambda: equal(order_row(db,oid)['order_status'],101))
    case('F014','下单扣减库存',lambda: equal(stock(db,p['id']),baseline-2))
    case('F015','订单详情与订单号关联',lambda: equal(check(actor.api.call('GET','/wx/order/detail',params={'orderId':oid}))['orderInfo']['id'],oid))
    check(actor.api.call('POST','/wx/order/cancel',body={'orderId':oid}))
    case('F016','取消订单状态变为102',lambda: equal(order_row(db,oid)['order_status'],102))
    case('F017','取消恢复原库存',lambda: equal(stock(db,p['id']),baseline))
finally:
    if actor: actor.cleanup()
    guest.close(); db.close()
    output=Path(__import__('os').environ['EVIDENCE_DIR'])/'results.json'
    output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':sum(x['status']=='passed' for x in results),'failed':sum(x['status']=='failed' for x in results)}))
sys.exit(any(x['status']=='failed' for x in results))
