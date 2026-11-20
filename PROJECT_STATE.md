# 当前维护快照

更新时间：2026-11-19 America/Los_Angeles。
项目：独立公开 DeepTutor 个性化档案；本地版本内容与此文件同属一个发布提交。
阶段：PPT/PPTX 已接入桌面和 CLI 后端的 PDF 阅读链路，桌面上传与翻页已验证。线上 SHA 以远端 main 为准。
Git 基线：73748252f9f4b3aa4028db5d304f5b784170d67b；本次维护分支 codex/paged-presentation-reading。

目标：公开可复现的完整改动、测试与开发时间线，持续保留隐私和上游许可边界。
本次范围：两套后端的 Office 转换服务、阅读存储与 API、对应补丁、哈希清单和合成回归脚本。
已完成验证：两套后端实际 LibreOffice 转换、无效文件拒绝、并发去重和旧记录升级；桌面真实上传、翻页和文字层。
尚未验证：完整上游测试集、新版本安装、CLI 网页交互。
决策：D4 复用 LibreOffice 和现有 PDF 阅读器。D1 至 D3 继续适用。
修改入口：docs/CHANGE_INVENTORY.md、upstream/manifest.json 和 archive/source-provenance.json。
授权边界：已授权后续 DeepTutor 成果同步；不包含私人运行数据或强制改写历史。
NEXT ACTION：维护新修改时按 docs/MAINTAINING.md 完成验证、脱敏导出与远端核验；没有待实施的本次功能改动。
证据：docs/VALIDATION.md 记录验证范围；WORK_LOG.md 记录本次导出；真实私有证据只留维护者本机。
