# 实际执行批次索引

| 目录 | 事实 |
| --- | --- |
| evidence/environment | 官方源码版本、Java/Maven/MySQL/前端安装与启动日志 |
| evidence/p0 | 初始尝试8个检查通过，随后测试账号BCrypt格式准备错误；不是17项完整通过 |
| evidence/p0-rerun | 修正测试数据后17项真实业务检查通过 |
| evidence/postman | Newman14请求、52断言及取消后SQL核对 |
| evidence/pytest-api-first | 33通过/3真实业务失败 |
| evidence/pytest-api-repeat | 正常33通过/3缺陷deselected |
| evidence/ui-inspection | GUI初查真实登录与SKU截图；首次placeholder定位问题后修正 |
| evidence/pytest-ui-first | 真实UI3通过/1详情取消失败；自动截图与Trace |
| evidence/runs/*-all | 交付Windows脚本完整40项：36通过/4失败，Allure HTML |
| evidence/runs/*-regression | 交付脚本正常回归；4个defect用例deselected |
| evidence/concurrency-smoke | 5线程50真实只读请求全部断言通过；原始耗时 |
| evidence/cleanup-verification.json | 清理后qa_run_用户0，货品1库存100 |

时间JSON使用UTC，展示日期采用香港时间。不会删掉首次测试代码失败的证据来制造一次成功的历史。

公开副本为精选证据：environment只保留provenance.json；早期批次只保留文本记录，初查截图及重复Allure/Trace未打包。完整40项批次的截图、Trace、Allure结果与报告均保留；原始完整本地工程未删除。
