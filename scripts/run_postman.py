from pathlib import Path
import sys, json, os, subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from framework.client import Db,Actor,product,stock,ROOT,config,evidence,order_row

def entry(name,method,path,body=None,errno=0,extra=(),auth=False):
    headers=[{'key':'Content-Type','value':'application/json'}]
    if auth: headers.append({'key':'X-Litemall-Token','value':'{{token}}'})
    request={'method':method,'header':headers,'url':'{{base_url}}'+path}
    if body is not None: request['body']={'mode':'raw','raw':json.dumps(body,ensure_ascii=False),'options':{'raw':{'language':'json'}}}
    tests=["pm.test('HTTP 200',()=>pm.response.to.have.status(200));",f"pm.test('业务码 {errno}',()=>pm.expect(pm.response.json().errno).to.eql({errno}));",
        "pm.test('响应结构',()=>pm.expect(pm.response.json().errmsg).to.be.a('string'));",*extra]
    return {'name':name,'request':request,'event':[{'listen':'test','script':{'type':'text/javascript','exec':tests}}]}

items=[
    entry('01 匿名商品查询','GET','/wx/goods/list?page=1&limit=2',extra=["pm.test('列表有商品',()=>pm.expect(pm.response.json().data.list.length).to.be.above(0));"]),
    entry('02 无Token购物车','GET','/wx/cart/index',errno=501),
    entry('03 缺失登录参数','POST','/wx/auth/login',{},errno=401),
    entry('04 账号密码登录','POST','/wx/auth/login',{'username':'{{username}}','password':'{{password}}'},extra=["pm.test('Token存在',()=>pm.expect(pm.response.json().data.token).to.be.a('string'));","if(pm.response.json().errno===0) pm.environment.set('token',pm.response.json().data.token);"]),
    entry('05 商品详情及规格','GET','/wx/goods/detail?id={{goods_id}}',extra=["pm.test('商品ID匹配',()=>pm.expect(pm.response.json().data.info.id).to.eql(Number(pm.environment.get('goods_id'))));"]),
    entry('06 数量零被拒绝','POST','/wx/cart/add',{'goodsId':'{{goods_id}}','productId':'{{product_id}}','number':0},errno=401,auth=True),
    entry('07 加入购物车','POST','/wx/cart/fastadd',{'goodsId':'{{goods_id}}','productId':'{{product_id}}','number':2},auth=True,extra=["pm.test('购物车ID',()=>pm.expect(pm.response.json().data).to.be.above(0));","if(pm.response.json().errno===0) pm.environment.set('cart_id',pm.response.json().data);"]),
    entry('08 购物车数量','GET','/wx/cart/index',auth=True,extra=["pm.test('购买数量2',()=>pm.expect(pm.response.json().data.cartTotal.goodsCount).to.eql(2));"]),
    entry('09 收货地址','POST','/wx/address/save',{'id':0,'name':'QA 测试','tel':'13800138000','province':'广东省','city':'深圳市','county':'南山区','areaCode':'440305','addressDetail':'Postman测试不发货','isDefault':True},auth=True,extra=["if(pm.response.json().errno===0) pm.environment.set('address_id',pm.response.json().data);"]),
    entry('10 提交待付款订单','POST','/wx/order/submit',{'cartId':'{{cart_id}}','addressId':'{{address_id}}','couponId':0,'userCouponId':0,'grouponRulesId':0,'grouponLinkId':0,'message':'Postman测试'},auth=True,extra=["pm.test('订单ID',()=>pm.expect(pm.response.json().data.orderId).to.be.above(0));","if(pm.response.json().errno===0) pm.environment.set('order_id',pm.response.json().data.orderId);"]),
    entry('11 查询订单详情','GET','/wx/order/detail?orderId={{order_id}}',auth=True,extra=["pm.test('订单关联',()=>pm.expect(pm.response.json().data.orderInfo.id).to.eql(Number(pm.environment.get('order_id'))));","pm.test('待付款可取消',()=>pm.expect(pm.response.json().data.orderInfo.handleOption.cancel).to.eql(true));"]),
    entry('12 提交后购物车清空','GET','/wx/cart/index',auth=True,extra=["pm.test('购物车清空',()=>pm.expect(pm.response.json().data.cartList).to.have.length(0));"]),
    entry('13 取消订单','POST','/wx/order/cancel',{'orderId':'{{order_id}}'},auth=True),
    entry('14 查询已取消订单','GET','/wx/order/detail?orderId={{order_id}}',auth=True,extra=["pm.test('取消状态',()=>pm.expect(pm.response.json().data.orderInfo.orderStatusText).to.eql('已取消'));"]),
]
collection={'info':{'name':'litemall 真实订单业务流','schema':'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},'item':items}
folder=ROOT/'postman'; folder.mkdir(exist_ok=True)
(folder/'litemall.postman_collection.json').write_text(json.dumps(collection,ensure_ascii=False,indent=2),encoding='utf-8')
template={'name':'litemall local (fill private values)','values':[{'key':k,'value':v,'enabled':True} for k,v in {
    'base_url':'http://127.0.0.1:8080','username':'<TEST_USERNAME>','password':'<TEST_PASSWORD>','goods_id':'<SQL_PRODUCT_GOODS_ID>',
    'product_id':'<SQL_PRODUCT_ID>','token':'','cart_id':'','address_id':'','order_id':''}.items()]}
(folder/'local.postman_environment.json').write_text(json.dumps(template,ensure_ascii=False,indent=2),encoding='utf-8')
db=Db(); actor=Actor.create(db); p=product(db); before=stock(db,p['id'])
private=folder/'run.private.json'
template['values']=[{'key':k,'value':v,'enabled':True} for k,v in {'base_url':config()['BASE_URL'],'username':actor.username,
    'password':config()['TEST_PASSWORD'],'goods_id':p['goods_id'],'product_id':p['id']}.items()]
private.write_text(json.dumps(template),encoding='utf-8')
out=Path(os.environ['EVIDENCE_DIR']); out.mkdir(parents=True,exist_ok=True)
try:
    result=subprocess.run(['node',str(ROOT/'.tools/newman/node_modules/newman/bin/newman.js'),'run',str(folder/'litemall.postman_collection.json'),
        '-e',str(private),'--reporters','cli,junit','--reporter-junit-export',str(out/'newman-junit.xml'),'--color','off'],capture_output=True,encoding='utf-8')
    (out/'execution.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    print(result.stdout[-2400:]); print('newman_exit_code',result.returncode)
    rows=db.query('SELECT id,user_id,order_status,goods_price,actual_price FROM litemall_order WHERE user_id=%s',(actor.id,))
    assert len(rows)==1 and rows[0]['order_status']==102
    assert stock(db,p['id'])==before
    evidence('postman-sql',{'orders':rows,'stock_before':before,'stock_after':stock(db,p['id']),'restored':True})
finally:
    private.unlink(missing_ok=True)
    actor.cleanup(); db.close()
sys.exit(result.returncode)
