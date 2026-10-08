from decimal import Decimal
import pytest,allure
from framework.client import Api,check,stock,order_row,evidence,config

pytestmark=[pytest.mark.api,allure.epic('开源商城业务与自动化测试')]

@allure.feature('账号鉴权')
@pytest.mark.parametrize('body,errno',[
    ({},401),({'username':'qa_missing'},401),({'password':'invalid'},401),
    ({'username':'','password':''},700),({'username':'qa_does_not_exist','password':'invalid'},700)
],ids=['empty-body','missing-password','missing-username','empty-strings','unknown-user'])
def test_login_invalid(guest,body,errno):
    check(guest.call('POST','/wx/auth/login',body=body),errno)

def test_login_wrong_password(guest,sut):
    check(guest.call('POST','/wx/auth/login',body={'username':sut.user.username,'password':'intentionally-invalid'}),700)

def test_login_success_and_token(sut):
    result=check(sut.user.api.call('GET','/wx/cart/index'))
    assert result['cartList']==[] and result['cartTotal']['goodsCount']==0
    row=sut.db.query('SELECT id,last_login_time FROM litemall_user WHERE id=%s',(sut.user.id,))[0]
    assert row['last_login_time'] is not None

@pytest.mark.parametrize('path',['/wx/cart/index','/wx/order/list','/wx/address/list'])
@pytest.mark.parametrize('token',[None,'invalid-token'],ids=['no-token','invalid-token'])
def test_token_required(path,token):
    api=Api(token)
    try: check(api.call('GET',path),501)
    finally: api.close()

@pytest.mark.parametrize('body,errno',[
    ({},401),({'username':'qa_registration','password':'invalid','mobile':'123','code':'000000'},707),
    ({'username':'qa_registration','password':'invalid','mobile':'13900139000','code':'000000'},703)
],ids=['required-fields','invalid-mobile','incorrect-code'])
def test_register_negative(guest,body,errno):
    check(guest.call('POST','/wx/auth/register',body=body),errno)

def test_sms_service_disabled(guest):
    check(guest.call('POST','/wx/auth/regCaptcha',body={'mobile':'13800138000'}),701)

@allure.feature('商品查询')
@pytest.mark.parametrize('limit',[1,2,10],ids=['min-one','two','default-ten'])
def test_goods_list_limits(guest,limit):
    data=check(guest.call('GET','/wx/goods/list',params={'page':1,'limit':limit}))
    assert 0<len(data['list'])<=limit and data['total']>=len(data['list'])
    assert all(isinstance(row['id'],int) and Decimal(str(row['retailPrice']))>=0 for row in data['list'])

def test_goods_detail_sql_consistency(sut,guest):
    p=sut.product
    data=check(guest.call('GET','/wx/goods/detail',params={'id':p['goods_id']}))
    assert data['info']['id']==p['goods_id'] and data['info']['name']==p['name']
    current=next(r for r in data['productList'] if r['id']==p['id'])
    assert current['number']==stock(sut.db,p['id']) and Decimal(str(current['price']))==p['price']

def test_goods_search(sut,guest):
    data=check(guest.call('GET','/wx/goods/list',params={'keyword':sut.product['name'],'page':1,'limit':20}))
    assert sut.product['goods_id'] in [r['id'] for r in data['list']]

@allure.feature('购物车')
@pytest.mark.parametrize('number',[-1,0])
def test_cart_invalid_quantity(sut,number):
    p=sut.product
    check(sut.user.api.call('POST','/wx/cart/add',body={'goodsId':p['goods_id'],'productId':p['id'],'number':number}),401)
    assert check(sut.user.api.call('GET','/wx/cart/index'))['cartList']==[]

def test_cart_over_stock(sut):
    p=sut.product
    check(sut.user.api.call('POST','/wx/cart/add',body={'goodsId':p['goods_id'],'productId':p['id'],'number':sut.baseline+1}),711)
    assert stock(sut.db,p['id'])==sut.baseline

def test_cart_missing_product(sut):
    check(sut.user.api.call('POST','/wx/cart/add',body={'goodsId':sut.product['goods_id'],'number':1}),401)

def test_cart_add_update_delete(sut):
    p=sut.product; cid=sut.user.cart(p,1)
    check(sut.user.api.call('POST','/wx/cart/add',body={'goodsId':p['goods_id'],'productId':p['id'],'number':1}))
    check(sut.user.api.call('POST','/wx/cart/update',body={'id':cid,'goodsId':p['goods_id'],'productId':p['id'],'number':3}))
    cart=check(sut.user.api.call('GET','/wx/cart/index'))
    assert cart['cartTotal']['goodsCount']==3 and Decimal(str(cart['cartTotal']['goodsAmount']))==p['price']*3
    assert sut.db.query('SELECT number FROM litemall_cart WHERE id=%s',(cid,))[0]['number']==3
    assert stock(sut.db,p['id'])==sut.baseline
    data=check(sut.user.api.call('POST','/wx/cart/delete',body={'productIds':[p['id']]}))
    assert data['cartList']==[]

def test_cart_cross_user_update_rejected(sut):
    victim=sut.new_actor(); p=sut.product; cid=victim.cart(p,1)
    check(sut.user.api.call('POST','/wx/cart/update',body={'id':cid,'goodsId':p['goods_id'],'productId':p['id'],'number':2}),402)
    assert sut.db.query('SELECT number FROM litemall_cart WHERE id=%s',(cid,))[0]['number']==1

@allure.feature('订单和库存')
@pytest.mark.parametrize('quantity',[1,2])
def test_order_create_cancel_business_flow(sut,quantity):
    p=sut.product; actor=sut.user; aid=actor.address(); cid=actor.cart(p,quantity)
    oid=check(actor.submit(cid,aid))['orderId']
    row=order_row(sut.db,oid)
    assert row['user_id']==actor.id and row['order_status']==101
    assert row['goods_price']==p['price']*quantity
    assert row['actual_price']==row['goods_price']+row['freight_price']
    lines=sut.db.query('SELECT product_id,number,price FROM litemall_order_goods WHERE order_id=%s',(oid,))
    assert len(lines)==1 and lines[0]['product_id']==p['id'] and lines[0]['number']==quantity
    assert stock(sut.db,p['id'])==sut.baseline-quantity
    detail=check(actor.api.call('GET','/wx/order/detail',params={'orderId':oid}))
    assert detail['orderInfo']['id']==oid and detail['orderInfo']['handleOption']['cancel'] is True
    assert check(actor.api.call('GET','/wx/cart/index'))['cartList']==[]
    check(actor.api.call('POST','/wx/order/cancel',body={'orderId':oid}))
    assert order_row(sut.db,oid)['order_status']==102 and stock(sut.db,p['id'])==sut.baseline
    canceled=check(actor.api.call('GET','/wx/order/detail',params={'orderId':oid}))
    assert canceled['orderInfo']['orderStatusText']=='已取消'
    response=actor.api.call('POST','/wx/order/cancel',body={'orderId':oid})
    assert response.status_code==200 and response.json()['errno']!=0
    assert stock(sut.db,p['id'])==sut.baseline, 'Repeated cancel must not increase stock twice'

def test_order_required_params(sut):
    check(sut.user.api.call('POST','/wx/order/submit',body={}),401)
    assert not sut.db.query('SELECT id FROM litemall_order WHERE user_id=%s',(sut.user.id,))

def test_empty_cart_no_order(sut):
    aid=sut.user.address()
    check(sut.user.submit(0,aid),402)
    assert not sut.db.query('SELECT id FROM litemall_order WHERE user_id=%s',(sut.user.id,))

def test_other_user_order_access_rejected(sut):
    owner=sut.new_actor(); oid=check(owner.submit(owner.cart(sut.product),owner.address()))['orderId']
    for method,path,body,params in [('GET','/wx/order/detail',None,{'orderId':oid}),('POST','/wx/order/cancel',{'orderId':oid},None)]:
        response=sut.user.api.call(method,path,body=body,params=params)
        assert response.status_code==200 and response.json()['errno']!=0
    assert order_row(sut.db,oid)['order_status']==101

@pytest.mark.defect
@allure.issue('BUG-001','缺少数量导致内部异常')
def test_missing_cart_number_should_be_validation_error(sut):
    p=sut.product
    response=sut.user.api.call('POST','/wx/cart/add',body={'goodsId':p['goods_id'],'productId':p['id']})
    evidence('BUG-001',{'response':response.json(),'stock':stock(sut.db,p['id'])})
    check(response,401)

@pytest.mark.defect
@allure.issue('BUG-002','跨用户购物车可被下单')
def test_submit_foreign_cart_must_be_rejected(sut):
    victim=sut.new_actor(); cid=victim.cart(sut.product,1); aid=sut.user.address()
    before=sut.db.query('SELECT id,user_id,product_id,number,deleted FROM litemall_cart WHERE id=%s',(cid,))
    response=sut.user.submit(cid,aid)
    after=sut.db.query('SELECT id,user_id,product_id,number,deleted FROM litemall_cart WHERE id=%s',(cid,))
    orders=sut.db.query('SELECT id,user_id,order_status FROM litemall_order WHERE user_id=%s',(sut.user.id,))
    evidence('BUG-002',{'victim_user':victim.id,'attacker_user':sut.user.id,'cart_id':cid,'cart_before':before,
        'cart_after':after,'orders':orders,'stock_before':sut.baseline,'stock_after':stock(sut.db,sut.product['id']),'response':response.json()})
    assert response.status_code==200
    assert response.json()['errno'] in [401,402,715], 'Foreign cart must be rejected without creating an order'
    assert after==before and not orders

@pytest.mark.defect
@allure.issue('BUG-003','商品与货品所属关系未校验')
def test_mismatched_goods_product_must_be_rejected(sut):
    p=sut.product
    foreign=sut.db.query('SELECT id,goods_id,price,number FROM litemall_goods_product WHERE deleted=0 AND number>0 AND goods_id<>%s ORDER BY id LIMIT 1',(p['goods_id'],))[0]
    response=sut.user.api.call('POST','/wx/cart/add',body={'goodsId':p['goods_id'],'productId':foreign['id'],'number':1})
    rows=sut.db.query('SELECT id,goods_id,product_id,goods_name,price FROM litemall_cart WHERE user_id=%s',(sut.user.id,))
    evidence('BUG-003',{'requested_goods':p['goods_id'],'foreign_product':foreign,'stored_cart':rows,'response':response.json()})
    assert response.status_code==200
    assert response.json()['errno'] in [401,402,713], 'Product must belong to the supplied goods'
    assert not rows
