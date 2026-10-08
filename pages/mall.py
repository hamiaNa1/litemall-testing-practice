import re,json
from playwright.sync_api import expect
from framework.client import config,evidence

def ui_response(response,errno=0):
    assert response.status==200
    body=response.json()
    evidence('ui-http',{'url':response.url,'status':response.status,'response':body})
    assert body['errno']==errno, f'UI business response expected {errno}, actual {body["errno"]}'
    return body.get('data')

class BasePage:
    def __init__(self,page): self.page=page; self.base=config()['UI_URL']
    def open(self,route): self.page.goto(self.base+'/#'+route,wait_until='domcontentloaded')

class LoginPage(BasePage):
    def login(self,username,password,errno=0):
        self.open('/login/')
        self.page.locator('input[name="user"]').fill(username)
        self.page.locator('input[name="password"]').fill(password)
        with self.page.expect_response(lambda r: '/wx/auth/login' in r.url and r.request.method=='POST') as info:
            self.page.get_by_role('button',name='登录',exact=True).click()
        ui_response(info.value,errno)
        if errno==0:
            expect(self.page).to_have_url(re.compile(r'.*#/user/.*'))
            expect(self.page.get_by_text(username,exact=True)).to_be_visible()
        else:
            expect(self.page).to_have_url(re.compile(r'.*#/login/.*'))

class SearchPage(BasePage):
    def search(self,name):
        self.open('/items/search')
        field=self.page.get_by_placeholder('请输入商品名称')
        field.fill(name)
        with self.page.expect_response(lambda r: '/wx/goods/list' in r.url) as info: field.press('Enter')
        return ui_response(info.value)
    def select(self,name):
        card=self.page.locator('.van-card').filter(has=self.page.get_by_text(name,exact=True))
        expect(card).to_have_count(1)
        card.click()
        expect(self.page.locator('.item-title')).to_have_text(name)

class ProductPage(BasePage):
    def add_to_cart(self,product):
        expect(self.page.locator('.item-title')).to_have_text(product['name'])
        self.page.get_by_role('button',name='加入购物车',exact=True).click()
        popup=self.page.locator('.van-sku-container')
        expect(popup).to_be_visible()
        specifications=json.loads(product['specifications'])
        for spec in specifications:
            popup.locator('.van-sku-row__item').filter(has_text=spec).click()
        with self.page.expect_response(lambda r:'/wx/cart/add' in r.url) as info:
            popup.get_by_role('button',name='加入购物车',exact=True).click()
        ui_response(info.value)
        expect(popup).not_to_be_visible()

class CartPage(BasePage):
    def checkout(self,name):
        self.open('/order')
        expect(self.page.get_by_text(name,exact=True)).to_be_visible()
        button=self.page.get_by_role('button',name='结算',exact=True)
        expect(button).to_be_enabled()
        button.click()
        expect(self.page).to_have_url(re.compile(r'.*#/order/checkout.*'))

class CheckoutPage(BasePage):
    def submit(self,name):
        expect(self.page.get_by_text(name,exact=True)).to_be_visible()
        expect(self.page.get_by_text('收货地址',exact=True)).to_be_visible()
        self.page.get_by_placeholder('请输入备注').fill('Playwright真实订单测试，无支付')
        with self.page.expect_response(lambda r:'/wx/order/submit' in r.url) as info:
            self.page.get_by_role('button',name='提交订单',exact=True).click()
        oid=ui_response(info.value)['orderId']
        expect(self.page).to_have_url(re.compile(r'.*#/order/payment.*'))
        return oid

class OrderListPage(BasePage):
    def cancel(self):
        self.open('/user/order/list/0')
        button=self.page.get_by_role('button',name='取消订单',exact=True)
        expect(button).to_be_visible()
        button.click()
        dialog=self.page.get_by_role('dialog')
        expect(dialog).to_be_visible()
        with self.page.expect_response(lambda r:'/wx/order/cancel' in r.url) as info:
            dialog.get_by_role('button',name='确认',exact=True).click()
        ui_response(info.value)
        expect(self.page.locator('.van-panel__header')).to_contain_text('已取消')

class OrderDetailPage(BasePage):
    def cancel(self,oid):
        self.open('/order/order-detail?orderId='+str(oid))
        button=self.page.get_by_role('button',name='取消订单',exact=True)
        expect(button).to_be_visible(); button.click()
        dialog=self.page.get_by_role('dialog')
        expect(dialog).to_be_visible()
        with self.page.expect_response(lambda r: bool(re.search(r'/wx/order/(delete|cancel)',r.url))) as info:
            dialog.get_by_role('button',name='确认',exact=True).click()
        response=info.value
        evidence('ui-http',{'url':response.url,'status':response.status,'response':response.json()})
        expect(dialog).not_to_be_visible()
        return response
