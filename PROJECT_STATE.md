# 当前维护快照

更新时间：2026-11-18 America/Los_Angeles。
项目：独立公开 DeepTutor 个性化档案；本地版本内容与此文件同属一个发布提交。
阶段：阅读资料排序已在桌面部署并通过实际菜单保存、重载验证；此快照随发布提交同步。线上 SHA 以远端 main 为准。
Git 基线：8fa7782d34a1b2887cda70a426229ea32c4b1aeb；本次维护分支 codex/reading-material-order。

目标：公开可复现的完整改动、测试与开发时间线，持续保留隐私和上游许可边界。
本次范围：桌面前端、两套后端的知识库与阅读同步、对应补丁、来源/哈希清单和合成回归脚本。
已完成验证：合成目录发布失败恢复、保存顺序持久化、后续追加与阅读进度；前端生产构建、定向检查与本机界面保存重载验证。
尚未验证：完整上游测试集、新版本安装、CLI 网页交互。
决策：D3 沿用资料组排序接口并在同步时保留已有顺序。D1、D2 继续适用。
修改入口：docs/CHANGE_INVENTORY.md、upstream/manifest.json 和 archive/source-provenance.json。
授权边界：已授权后续 DeepTutor 成果同步；不包含私人运行数据或强制改写历史。
NEXT ACTION：维护新修改时按 docs/MAINTAINING.md 完成验证、脱敏导出与远端核验；没有待实施的本次功能改动。
证据：docs/VALIDATION.md 记录验证范围；WORK_LOG.md 记录本次导出；真实私有证据只留维护者本机。
