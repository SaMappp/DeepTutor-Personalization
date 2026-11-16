# 当前维护快照

更新时间：2026-11-16 America/Los_Angeles。
项目：独立公开 DeepTutor 个性化档案；本地版本内容与此文件同属一个发布提交。
阶段：上下文调查复用代码和本机部署已验证；此快照随发布提交同步。线上 SHA 以远端 main 为准。
Git 基线：dfccde319b79b77f54603ba08d92c25f040f328f；本次维护分支 codex/context-investigation-reuse。

目标：公开可复现的完整改动、测试与开发时间线，持续保留隐私和上游许可边界。
本次范围：桌面后端四个模块、完整 desktop 补丁、来源/哈希清单、测试、脱敏维护脚本和文档。
已完成验证：本机四文件部署与重启，原消息/附件保留校验；14 项离线回归；两轮真实合成资料对话。
本次公开副本验证：81 个 Python 文件解析成功、四组干净基线补丁逐字节复现、16 项默认测试及 14 项能力/工具检查通过；隐私扫描无命中。
尚未验证：任意新平台的安装、完整上游测试集和用户长会话的后续速度。不把合成测试耗时当作性能承诺。
决策：D1 仅桌面复用调查并保留按需原文读取；D2 完成并验证后按白名单同步。
修改入口：docs/CHANGE_INVENTORY.md、upstream/manifest.json 和 archive/source-provenance.json。
授权边界：已授权后续 DeepTutor 成果同步；不包含私人运行数据或强制改写历史。
NEXT ACTION：维护新修改时按 docs/MAINTAINING.md 完成验证、脱敏导出与远端核验；没有待实施的本次功能改动。
证据：docs/VALIDATION.md 记录验证范围；WORK_LOG.md 记录本次导出；真实私有证据只留维护者本机。
