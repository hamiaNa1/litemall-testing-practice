# Windows 部署和运行记录

## 实际环境

源码：[linlinjava/litemall](https://github.com/linlinjava/litemall)，GitHub API返回提交`a1ef964a718b7277925b19ea26afe78ea3a1d325`；下载来源和SHA256见`evidence/environment/provenance.json`。

Python 3.10.11、Node 24.20.0和MySQL 8.4.11程序使用已有安装。初查PATH未找到Java/Maven，项目免安装JDK8和Maven放在`.tools`，不改系统注册表/PATH。Maven构建完成（上游默认跳过其自带单测，此记录不是上游单测通过声明）。Vue2/webpack4保持原架构。

| 组件 | 位置/入口 |
| --- | --- |
| 项目 | [PROJECT] |
| JDK8 | .tools/zulu8.96.0.205-ca-jdk8.0.504-win_x64 |
| Maven3.9.9 | .tools/apache-maven-3.9.9 |
| MySQL程序 | D:\DevTools\MySQL\mysql-8.4.11-winx64\bin |
| 独立数据 | .runtime/mysql-data，端口13306，库litemall_qa |
| Python | .venv，精确依赖requirements.txt |
| 前端 | vendor/litemall-master/litemall-vue，端口6255 |
| 后端 | litemall-all-0.1.0-exec.jar，端口8080 |
| Allure2.34.1 | .tools/allure-2.34.1 |
| 下载/缓存 | D:\Codex\Downloads\mall-testing；D:\Codex\Cache |

## 实际解决的环境问题

1. GitHub Git通道连接重置，官方codeload压缩包可下载；未改用Mock或重写商城。
2. SQL原始schema会DROP DATABASE，未执行该文件。在验证过的项目独立空库导入table/data时去掉DROP TABLE行，既有3306数据库不受影响。MySQL绑定127.0.0.1，不注册新系统服务。
3. 首次测试数据准备使用BCrypt `$2b$`导致登录700；读商城BCrypt源码确认只支持`$2a$`，修正测试数据生成器并清理那次失败账号。原始尝试在`evidence/p0/`，重跑17项通过在`evidence/p0-rerun/`。
4. 前端编译缺`regenerator-runtime/runtime`，只补`regenerator-runtime@0.14.1`并保存锁文件`config/frontend-package-lock.json`。Node24下webpack4通过进程级`NODE_OPTIONS=--openssl-legacy-provider`启动，没有升级Vue或修改业务代码。
5. UI初查发现placeholder同时在容器和input上；POM使用明确`input[name=user/password]`，没有使用固定sleep来掩盖定位问题。

## 完成setup后的本地启动

```powershell
Set-Location D:\Codex\Projects\litemall-testing-practice
.\scripts\start.ps1
.\scripts\run-tests.ps1 -Suite all
.\scripts\open-report.ps1
```

`start.ps1`从忽略的`.env`读取环境变量，以外部qa profile配置独立数据库。验证码、邮件、微信支付未调用外部服务。用户名与密码用本机`.env`查看，勿粘贴到日志。

## 新机器/依赖恢复

安装已有版本范围的Python3.10、Node24、Git和MySQL8程序后执行：

```powershell
$env:MYSQL_BIN='D:\DevTools\MySQL\mysql-8.4.11-winx64\bin'
.\scripts\setup.ps1
.\scripts\start.ps1
```

setup保存锁定上游提交、工具和Python/npm依赖；项目启动脚本、pip依赖安装、Maven构建、前端安装、数据库初始化在本机已分别真实执行。完整新机器从零setup下载流程没有跨机器验证，网络不可用时会失败并保存日志，不标为已验证的跨机器部署。

`.env`首次由provision生成随机密码，不要用`.env.example`覆盖已有`.env`。SQL测试只允许loopback与litemall_qa。浏览器优先复用现有D盘Chromium，也可通过`CHROMIUM_EXECUTABLE`指定路径。

## 日志、报告与排障

公开包只精选历史业务证据；安装/运行日志由本机setup/start重新生成，未打包完整历史环境日志。[PROJECT]表示原机器路径已脱敏，克隆后的实际位置以本机目录为准。

- 后端启动/错误：`evidence/environment/backend.stdout.log`、`backend.stderr.log`和实时`logs/error.log`。
- 构建：`maven-build.log`；前端部署：`npm-vue-install.log`、`frontend-dependency-fix.log`。
- 接口：每批`http.jsonl`和`pytest.log`；数据库：`sql.jsonl`；清理：`cleanup.jsonl`。
- Allure需HTTP提供静态文件，直接file://打开可能加载失败。`open-report.ps1`不调用付费服务。
- 查看Trace：`.\.venv\Scripts\python.exe -m playwright show-trace <evidence中trace.zip的完整路径>`。已脱敏的Trace可保留动作与网络结构，原始敏感内容不保留。
- 初始数据库货品1库存100，取消后必须恢复100。示例订单ID每次不同；测试数据清理后应看保存的SQL快照，不把数据库查不到已清理订单当成商城缺陷。
- 本环境不是Linux，没有声称实际执行Linux日志诊断。

## 交付后的操作核验

停止和重新启动脚本已真实执行，重启后商品总数238、登录页可见、货品1库存100、测试账号残留0，证据为 evidence/delivery-validation/restart-verification.json。

Allure浏览器验证截图：evidence/delivery-validation/allure-overview.png，JSON核对总数40/通过36/失败4/跳过0。数据库端口隔离加强后，订单业务针对性验证2通过，证据为 evidence/fixture-guard-verification/junit.xml。

只读SQL文件已通过MySQL客户端实际执行，结果在 evidence/sql-script/。运行命令：

```powershell
$env:EVIDENCE_DIR="$PWD\evidence\sql-script-new"
.\.venv\Scripts\python.exe .\scripts\run_sql.py
```

open-report.ps1默认展示交付的完整报告；查看新批次请传 -RunDirectory '新的evidence/runs目录'，已有另一报告占用端口时加 -Port 8766。
