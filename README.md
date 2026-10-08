# 开源商城业务功能与自动化测试

项目仓库：<https://github.com/hamiaNa1/litemall-testing-practice>

面向初级功能测试、接口测试岗位的真实实战项目，以 Python 自动化作为补充能力。被测系统是未修改业务逻辑的开源 litemall，所有接口访问本地 Spring Boot 服务和独立 MySQL，不使用 Mock 或付费 AI API。


## 招聘方快速查看

- [真实缺陷与复现证据](docs/BUG_REPORTS.md)：包含越权下单、商品货品错配、参数校验与UI取消问题。
- [完整40项结果](evidence/runs/20261008-150847-all/summary.json)：36通过 / 4失败 / 0跳过；4个缺陷未修复。
- [失败截图](evidence/runs/20261008-150847-all/ui/test_ui_detail_cancel_should_cancel_order/failure.png)与[Allure总览](evidence/delivery-validation/allure-overview.png)。
- [接口自动化](tests/api/test_business.py)、[UI页面封装](pages/mall.py)、[SQL核对](sql/verify_business.sql)、[Postman集合](postman/litemall.postman_collection.json)。
- [公开证据说明](docs/PUBLIC_EVIDENCE.md)、[Windows部署](docs/WINDOWS_SETUP.md)、[面试资料](INTERVIEW_GUIDE.md)。

无需启动商城即可查看历史Allure：在仓库根目录运行 `python -m http.server 8766 --bind 127.0.0.1 --directory evidence/runs/20261008-150847-all/allure-report`，浏览器访问 <http://127.0.0.1:8766>。GitHub文件预览不能直接运行Allure网页。

本仓库展示真实本地测试，未声称生产项目、支付测试或商城开发经历；不同批次用例重叠，数量不可直接相加。

## 实际结果（2026-10-08，香港时间）

| 执行批次 | 通过 | 失败 | 跳过 | 说明 |
| --- | ---: | ---: | ---: | --- |
| P0业务检查 | 17 | 0 | 0 | 真实API执行、订单/库存SQL核对 |
| Postman/Newman | 52断言 | 0 | 0 | 14真实请求；未声称手工打开Postman GUI |
| pytest接口 | 33 | 3 | 0 | 3个未修复商城缺陷 |
| Playwright页面 | 3 | 1 | 0 | 真实Chromium操作；取消详情按钮缺陷 |
| pytest完整批次 | **36** | **4** | **0** | **40用例，0环境错误**；退出码1如实保留 |

不同批次有重叠场景，不应把以上数字相加当作独立覆盖数。成功注册因本地短信服务关闭而受阻，不是pytest跳过项。测试代码准备账号的SQL INSERT不等于测试了成功注册。

## 当前机器立即运行

```powershell
Set-Location D:\Codex\Projects\litemall-testing-practice
.\scripts\start.ps1
.\scripts\run-tests.ps1 -Suite regression  # 正常回归36项；显式排除4个缺陷用例
.\scripts\run-tests.ps1 -Suite all         # 完整40项；4项仍应失败，表示缺陷未修复
.\scripts\open-report.ps1                 # http://127.0.0.1:8765
```

商城前端：<http://127.0.0.1:6255>；接口：<http://127.0.0.1:8080>；独立MySQL：`127.0.0.1:13306 / litemall_qa`。可视页面演示使用`.env`中的`TEST_USERNAME/TEST_PASSWORD`，密码不写入报告。

首次恢复工具/依赖时执行`.\scripts\setup.ps1`，详见[Windows部署文档](docs/WINDOWS_SETUP.md)。停止本项目服务执行`.\scripts\stop.ps1`。

## 查看交付物

- [测试用例CSV](docs/test_cases.csv)与`docs/test_cases.xlsx`：步骤、断言、实际结果和证据。
- [测试计划](docs/TEST_PLAN.md)、[测试总结](docs/TEST_SUMMARY.md)、[逐项验收](docs/ACCEPTANCE.md)。
- [Postman集合](postman/litemall.postman_collection.json)与环境模板；实际结果在`evidence/postman/`。
- `framework/client.py`、`tests/api/test_business.py`：请求、鉴权、参数化、SQL断言、数据清理。
- `pages/mall.py`、`tests/ui/`：POM、真实页面流程、截图和脱敏Trace。
- [只读SQL脚本](sql/verify_business.sql)、`evidence/**/sql.jsonl`：订单、金额、库存及权限证据。
- [缺陷报告](docs/BUG_REPORTS.md)：4项真实未修复缺陷。
- [面试准备](INTERVIEW_GUIDE.md)：基于实际实现与结果，不夸大为生产项目。
- 完整报告：`evidence/runs/20261008-150847-all/allure-report/`；原始结果：`allure-results/`；精确统计：`summary.json`。

## 独立执行接口测试与Postman

```powershell
$env:EVIDENCE_DIR="$PWD\evidence\manual-api"
.\.venv\Scripts\python.exe -m pytest tests/api -m 'not defect' -q --alluredir "$env:EVIDENCE_DIR\allure-results"
$env:EVIDENCE_DIR="$PWD\evidence\manual-postman"
.\.venv\Scripts\python.exe .\scripts\run_postman.py
```

Postman GUI可导入集合和`local.postman_environment.json`，在本机填写环境变量，勿导出带真实密码或Token的环境文件。推荐wrapper运行，会动态准备专用用户并清理；集合包含Token/cartId/addressId/orderId关联和52个断言。

## 已知限制与数据边界

- 成功注册、微信授权登录、支付/退款、管理后台商品创建、完整浏览器兼容性与大负载性能未覆盖。
- 核心UI只测Chromium手机视口390×844；图片部分依赖上游外链，不用图片加载完成作为业务等待条件。
- 4项缺陷未修复；`-m defect`是失败断言，未使用xfail/skip掩盖。正常回归排除缺陷时显示deselected。
- 每测试生成`qa_run_`唯一账号，只按已知用户ID清理其地址/购物车/订单等记录，先取消待付款订单恢复库存。原始快照保存在报告，清理后数据库不保留这些订单。
- `.env`、商城vendor、工具、虚拟环境、运行数据库和实时服务日志均被Git忽略；发布副本不包含本地凭证及运行环境。

## 新机器取得项目

使用项目仓库HTTPS地址执行：

```powershell
Set-Location D:\Codex\Projects
git clone https://github.com/hamiaNa1/litemall-testing-practice.git litemall-testing-practice
Set-Location .\litemall-testing-practice
$env:MYSQL_BIN='<现有MySQL安装目录>\bin'
.\scripts\setup.ps1
.\scripts\start.ps1
.\scripts\run-tests.ps1 -Suite all
```

仓库当前不内置密码；setup首次自动生成忽略的`.env`，不要用模板覆盖已有配置。历史报告的订单ID和测试账号已清理，SQL重新运行应结合新批次快照判断。

上游来源与许可见[第三方说明](THIRD_PARTY.md)。简历表述见[项目链接与简历说明](docs/RESUME_PROJECT.md)。公开发布前检查见[发布核验](docs/PUBLISH_CHECKLIST.md)。
