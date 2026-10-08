# 发布与验收

目标Public仓库已核验：<https://github.com/hamiaNa1/litemall-testing-practice>。项目所有者于2026-10-08明确授权首次commit和push。RELEASE_AUDIT.json保存提交前的核验快照，最终是否上传以GitHub仓库内容为准。

1. 阅读PUBLIC_EVIDENCE.md和RELEASE_AUDIT.json，核对40/36/4/0结果与4项缺陷。
2. 使用Git Credential Manager完成GitHub认证；凭证不进入项目文件或日志。
3. 首次提交使用main分支，只提交经脱敏核验的公开副本；提交者邮箱使用GitHub noreply地址。
4. 上传后使用未登录浏览器检查README、缺陷截图、代码与证据能否访问，再把实际仓库HTTPS地址加入简历。
5. 可选GitHub Pages仅发布静态Allure，不是部署商城；本次未启用Pages。

不要上传原始本地运行工程整体，不上传.env、.runtime、vendor、.tools、.venv、storage。后续运行生成的新报告需重新脱敏审查。无既有Git历史，本次不存在历史泄漏核验对象；未核验远端访问权限或跨机器从零部署。
