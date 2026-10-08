import pytest,allure
from playwright.sync_api import expect
from framework.client import config,check,stock,order_row,evidence
from pages.mall import LoginPage,SearchPage,ProductPage,CartPage,CheckoutPage,OrderListPage,OrderDetailPage

pytestmark=[pytest.mark.ui,allure.epic('开源商城业务与自动化测试'),allure.feature('真实 Chromium 页面流程')]

def test_ui_login_wrong_password(sut,ui_page):
    LoginPage(ui_page).login(sut.user.username,'intentionally-invalid',errno=700)
    expect(ui_page.get_by_text('账号密码不对',exact=True)).to_be_visible()

def test_ui_search_product(sut,ui_page):
    LoginPage(ui_page).login(sut.user.username,config()['TEST_PASSWORD'])
    data=SearchPage(ui_page).search(sut.product['name'])
    assert sut.product['goods_id'] in [row['id'] for row in data['list']]
    SearchPage(ui_page).select(sut.product['name'])
    expect(ui_page.get_by_text('商品详情',exact=True)).to_be_visible()

def test_ui_create_order_cancel_from_list(sut,ui_page):
    # Only the address is prepared via the real API; all main shopping actions use the UI.
    sut.user.address()
    LoginPage(ui_page).login(sut.user.username,config()['TEST_PASSWORD'])
    SearchPage(ui_page).search(sut.product['name'])
    SearchPage(ui_page).select(sut.product['name'])
    ProductPage(ui_page).add_to_cart(sut.product)
    cart=sut.db.query('SELECT product_id,number FROM litemall_cart WHERE user_id=%s AND deleted=0',(sut.user.id,))
    assert len(cart)==1 and cart[0]['product_id']==sut.product['id'] and cart[0]['number']==1
    CartPage(ui_page).checkout(sut.product['name'])
    oid=CheckoutPage(ui_page).submit(sut.product['name'])
    assert order_row(sut.db,oid)['order_status']==101
    assert stock(sut.db,sut.product['id'])==sut.baseline-1
    OrderListPage(ui_page).cancel()
    assert order_row(sut.db,oid)['order_status']==102
    assert stock(sut.db,sut.product['id'])==sut.baseline

@pytest.mark.defect
@allure.issue('BUG-004','订单详情取消按钮调用删除接口')
def test_ui_detail_cancel_should_cancel_order(sut,ui_page):
    oid=check(sut.user.submit(sut.user.cart(sut.product),sut.user.address()))['orderId']
    LoginPage(ui_page).login(sut.user.username,config()['TEST_PASSWORD'])
    response=OrderDetailPage(ui_page).cancel(oid)
    row=order_row(sut.db,oid)
    evidence('BUG-004',{'order_id':oid,'requested_url':response.url,'response':response.json(),'sql_order':row,
        'stock_before_order':sut.baseline,'stock_after_click':stock(sut.db,sut.product['id'])})
    assert row['order_status']==102, 'Confirming cancel on the detail page must cancel the pending order'
    assert stock(sut.db,sut.product['id'])==sut.baseline
