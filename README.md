# DeepTutor-Personalization

基于 [HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor) **v1.7.1** 的个人改造代码、补丁和开发过程档案。维护者：**SaMappp**。

这是个人维护的非官方扩展仓库。DeepTutor 原项目及其贡献者保留原有署名和权利。这里保存安装以来的个性化开发成果，并明确区分官方功能、个人改动和发布时的脱敏适配。

**上游基线：** `f7aed0744c36c5afef16a4261c31ebee1208cac2`。首次整理发布：2026-11-10。

## 已做的改造

| 阶段 | 具体成果 | 使用范围 |
|---|---|---|
| 安装与迁移 | 官方 PyPI 完整版、独立桌面版；本机监听、可靠启动/停止、目录迁移与工作区路径修复 | CLI/PyPI 与 Windows 桌面版 |
| 模型使用 | 区分订阅、企业积分和账号余额来源；默认模型与临时模型选择分开 | 两套独立设置 |
| 推理强度 | 聊天输入区选择模型支持的推理等级；保存中禁止发送，失败保留原值 | 前端＋后端参数映射 |
| 学习辅助 | 本地 Jina embedding、Whisper 转写、Edge 在线朗读转接；按需启动与空闲退出 | 独立本机服务 |
| 文档转换 | PPT→PDF、PDF→图片PPT；内容去重、原件保留、重复执行与课程导入脚本 | 独立 Windows 工具 |
| PDF/OCR | 本地中文 OCR、可搜索 PDF、部分页处理、缓存、暂停续作及 GUI | 独立工具 |
| 原生按页 OCR | 沉浸式阅读只识别所需扫描页；缓存复用、并发合并、失败重试与进度提示 | **仅桌面后端** |
| 文档与章节读取 | 完整作业、Part/章节任务支持跨页；原生文字和已有缓存不受当前截图范围限制，新增 OCR 仍按需 | **仅桌面后端，2026-11-12 修复** |
| 知识库与阅读 | 上传资料自动加入所属工作区的阅读合集；内容去重，保留原批注与进度 | 两套后端分别同步 |
| 阅读与桌面修复 | 伴读模型/强度菜单向上展开；Windows 恢复窗口时刷新内嵌视图尺寸 | 前端／Electron 壳 |

完整经过见 [开发时间线](docs/DEVELOPMENT_HISTORY.md)，逐项文件映射见 [改动清单](docs/CHANGE_INVENTORY.md)。

## 仓库内容

- `overrides/`：当前改造的完整源文件，按 CLI、桌面后端、前端和桌面壳分开。
- `patches/`：4 组相对于官方 v1.7.1 的补丁。CLI 与桌面后端补丁二选一。
- `archive/workspace/`：安装、转换、部署、验收脚本及原说明的脱敏历史副本；保留原来的目录关系。
- `tools/`、`tests/`：补丁复现检查、显式 API 配置工具及其测试。
- `examples/`：不含凭据的配置示例和目录布局。
- `docs/`：时间线、复现步骤、验证边界、发布范围和分区许可。
- `upstream/manifest.json`：固定基线、目标路径、修改前后 SHA-256；`archive/source-provenance.json` 记录归档来源与脱敏副本哈希。

没有复制整个官方项目。完整上游源码请从官方仓库取得；本仓库提供个人改动的全部目标文件和可核对补丁。原始目录没有个人开发提交，因此历史以文档记录；本仓库的提交日期是整理发布日期。

## 查看和复现

先阅读 [复现与维护](docs/REPRODUCING.md)。检查归档自身不需要账号：

```powershell
python tools/verify_publication.py
python -m unittest discover -s tests -v
```

对照干净的官方 v1.7.1 源码检查全部补丁：

```powershell
python tools/verify_publication.py --upstream C:/path/to/official-DeepTutor-v1.7.1
```

历史工具包含 Windows、同级目录、已安装依赖及本地配置假设，不能直接当成通用安装器。公开版原生 OCR 使用 `DEEPTUTOR_NATIVE_OCR_CONFIG` 指定配置文件，默认指向用户目录下的 `DeepTutor-native-ocr/configuration.json`。

## 公开范围与许可

本仓库只包含代码和整理说明。**不包含密钥、登录令牌、原始聊天、学习数据库、课程课件、教材、OCR 文字缓存、钱包信息或模型权重。** 原 DeepWorks 客户端凭据提取实现未公开；通用替代工具由使用者显式提供获准使用的 API 配置，见 [模型接入说明](docs/PROVIDER_INTEGRATIONS.md)。

DeepTutor 衍生文件保留 **Apache-2.0**；新增独立 PDF/OCR 与学习辅助工具采用 **AGPL-3.0-or-later**，具体以文件声明和 [许可范围](docs/LICENSING.md) 为准。上游许可证、署名和第三方声明均保留；依赖和模型需另行安装并遵守各自许可。这里没有官方背书，也没有将第三方服务账号权限作为开源许可授予。

历史验证与本次发布检查分别记录于 [验证记录](docs/VALIDATION.md)。未宣称支持新版本或在其他电脑完成验收。

---

English: An **unofficial**, independently hosted archive of personal DeepTutor v1.7.1 customizations. It includes full changed source files, reproducible patches, sanitized historical tooling and a development timeline. No private learning data or credentials are distributed. Upstream-derived code retains Apache-2.0; independent PDF/OCR and support tooling is AGPL-3.0-or-later where marked. See the linked documentation for installation assumptions, licensing boundaries and verification limits.
