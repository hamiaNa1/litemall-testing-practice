# 面试项目介绍与技术追问

## 约一分钟介绍

我用开源litemall搭建了本地测试环境，重点测试商品、购物车、订单和库存，而不是自己开发商城。先根据页面、控制器和数据库分析流程，用等价类、边界值和场景法设计用例，再通过真实接口与SQL执行。P0业务检查17项通过，Postman集合14请求、52个断言通过。pytest完整40项中36通过、4失败，这4项是实际未修复商城缺陷。Playwright用POM走通了登录、商品搜索、选规格、加购、下单和订单列表取消。报告保留接口响应、SQL、截图和Trace。

可主动说明：成功注册受短信服务关闭阻塞，账号由SQL fixture准备；没有测试真实支付；这是求职练习项目，不是生产工作经历。

## 订单如何分析

按身份、商品/SKU、购物车、收货地址、订单、库存六个对象画关系。Token代表用户；cartId与addressId应属于本人；productId应属于goodsId。登录后查商品→加购物车→下单101→取消102。加购不扣库存，下单扣数量，取消加回。检查金额=明细单价×数量+运费−优惠，订单所属用户、明细、购物车清理和库存同时核对。

代码：`test_order_create_cancel_business_flow`实际参数数量1和2；不依赖固定订单ID。SQL查询订单/明细/货品，重复取消必须失败且不多恢复库存。

## 如何设计测试用例

等价类：正确/错误账号密码、缺字段、合法/非法手机号、有效/伪造Token。边界值：购物车-1、0、1、2、库存+1，分页1/2/10。场景法：正常下单取消、重复取消、空购物车、A/B用户越权。数据关联：商品与别的商品SKU错配。实际没有覆盖全部字段长度或所有并发边界，不能声称覆盖率100%。

## 为什么pytest，fixture和参数化如何用

pytest断言直接、fixture依赖和teardown清晰、参数化便于同一业务规则覆盖多输入，能接Allure和Playwright。它不是因为“行业最先进”而选择，实际适合这个Python工程。

`db` session fixture建立连接，`sut`函数fixture生成唯一qa_run_账号、登录、记录库存基线，yield后取消待付款订单再定向清理。`guest`只创建无Token Session。参数化覆盖5组非法登录、6组Token鉴权、3组注册异常、3种分页等。密码从.env读取，不作为参数化测试名称。

为什么不直接session固定用户？共享购物车和订单会互相污染，失败后残留会影响下一次；唯一用户+清理更稳定。为何写测试不并行？当前共享种子库存，库存断言需要串行；不能直接开xdist后仍假设独占库存。

## Token关联如何实现

`Actor.create`调真实login，断言业务成功后从`data.token`提取，存requests.Session头`X-Litemall-Token`。随后cart/address/order共享Session。Postman test脚本用`pm.environment.set`保存token和cartId/addressId/orderId。没有把Token硬编码进代码，也不把业务errno501误当HTTP401。

## 接口断言和数据库断言

`check`先断言HTTP、响应结构、errno和errmsg，再在测试里检查商品ID、金额、数量、订单状态/归属；只看HTTP200会漏掉errno502或725。业务错误也往往HTTP200。

SQL核对订单101/102、明细productId/数量/金额、库存基线与变化、购物车deleted，以及用户归属。金额用Decimal，不用浮点直接算财务金额。DB查询记录在sql.jsonl并附Allure。清理后订单查不到是预期，因此执行时快照必须保存。

## 如何讲一个真实Bug

推荐BUG-002：A/B各自登录，B创建cartId，A带B cartId和自己的addressId下单。接口竟返回成功，SQL证实订单归A、B购物车deleted=1、库存少1。比较order/detail/cancel和cart/update可知其他入口有用户约束，而submit非零cartId分支只按id查；这是权限遗漏。复现只有独立本地测试用户，无生产数据。报告有HTTP/SQL和失败断言，最后fixture取消A订单恢复库存。

可追问BUG-004：详情页取消点击发的是order/delete，返回725、SQL仍101；列表取消发order/cancel正常。定位链路是页面动作→网络URL→Vue cancelOrder调用→接口业务码→SQL，源码证据是调用错函数。未修复，不能说“修复回归已通过”。

BUG-001缺少number会NPE，是参数校验顺序问题；BUG-003分别查goods和product却未校验所属关系，商品名和价格错配。详见实际缺陷报告。

## 如何提高UI稳定性

POM把input[name=user/password]、角色按钮、商品卡片、SKU弹窗定位封装起来。使用expect响应、URL和可见状态自动等待，不做固定sleep。接口只准备地址；核心购物流程是真实UI点击。每用例独立浏览器context，测试账号隔离。失败自动截图，Trace包含动作/网络；测试密码和登录Token在Trace/报告中脱敏。外链图片不是业务成功条件。

## 如何区分问题来源

最初BCrypt2b对旧商城2a不兼容是测试数据问题，改fixture哈希版本后真实登录通过。placeholder容器和input重复是测试定位问题，修POM。regenerator-runtime缺失是部署依赖问题，仅补运行时依赖。四个报告缺陷在测试框架正常工作时触发真实业务断言，不能归咎pytest。

## 常见追问与诚实边界

- 数据清理失败怎么办：teardown报错，不忽略；账号唯一可按cleanup.jsonl和SQL追踪，不大范围DELETE。
- 所有测试通过吗：完整36通过/4失败/0跳过；正常回归排除未修复缺陷，不声称修好了。
- 性能测试做了什么：只有5线程50次只读请求的本机烟测；没有JMeter/容量/稳定性结论。
- 是否Mock：没有；requests和浏览器都访问真实SpringBoot，SQL查独立MySQL。
- 哪些还没做：有效短信成功注册、微信登录、支付退款、管理员写功能、多浏览器、生产负载和Linux实际诊断。
- 应聘定位：能做业务分析、用例设计、接口/SQL验证和真实Bug定位的初级功能/接口测试工程师；具备Python自动化优势，不把项目描述为高级测试开发平台。
