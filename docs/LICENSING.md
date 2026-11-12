# 许可、署名与发布规则

本仓库按组件标记许可，不能把所有依赖、模型或服务统称为 Apache-2.0。维护者已确认按下表公开。

| 范围 | 许可／说明 |
|---|---|
| 上游 DeepTutor 衍生文件、相应补丁中的原有内容 | Apache-2.0；保留原署名，附修改声明 |
| 新增原生 OCR 与任务范围模块 `overrides/desktop/deeptutor/reading/native_ocr.py`、`page_scope.py` | AGPL-3.0-or-later |
| `archive/workspace/DeepTutor-conversion-tools/`、`DeepTutor-native-ocr/`、`DeepTutor-learning-support/` 新增独立工具 | AGPL-3.0-or-later，文件头及相应目录 LICENSE 标记 |
| 其他本仓库新增源码、整理文档及配置示例 | Apache-2.0，除非文件另有声明 |
| 上游保留的第三方内容 | 保持 `THIRD_PARTY_NOTICES.md` 中原许可与署名 |
| 外部依赖、模型、字体、网络服务 | 各自许可／条款；不由本仓库许可重新授权 |

根目录 `LICENSE` 和 `LICENSES/Apache-2.0.txt` 为官方 v1.7.1 原许可证；`LICENSES/AGPL-3.0.txt` 为 AGPL v3 全文。混合补丁中每个文件以自己的声明为准。含新增 OCR 模块的整体组合使用／再分发还需满足 AGPL，不能只引用根许可证就称整个 PDF/OCR 组合仅为 Apache。

## 本次采取的措施

- 固定并链接上游 v1.7.1 与 commit，清楚声明非官方个人改造，不冒用官方背书。
- 在修改后的上游文件开头增加显著修改说明；完整补丁、源码及哈希清单可互相核对。
- 保留 Apache-2.0、原有版权／署名及全部官方 `THIRD_PARTY_NOTICES.md` 内容；附本仓库 `NOTICE`。
- 首次整理时没有在官方分发根找到额外名为 `NOTICE` 的文件；若以后换基线应重新核查。
- 课程、教材、原始页面、OCR 内容、字体、官方程序及依赖二进制不随仓库再分发。
- 不上传密钥、令牌、原始聊天、账号余额或学习数据库；不把服务账号使用权作为软件许可转授。
- 没有向上游提交 PR、issue 或消息。以后主动回馈代码应按上游贡献指南选择 `dev` 或相应目标分支，避免把个人数据和环境改动混入。

## 外部组件

PyMuPDF／MuPDF 提供 AGPL 与商业许可选项。本仓库新增独立 PDF/OCR 工具采用 AGPL-3.0-or-later；没有分发 PyMuPDF 二进制，也没有取得或暗示包含商业许可。若以后分发打包程序或提供网络服务，需要按实际组合继续履行源码、声明及相关义务。

RapidOCR、ONNX Runtime、PP-OCR 模型、Jina 模型、Whisper/faster-whisper、Edge TTS 客户端、LibreOffice 和备用 pdf2pptx 需要另行取得。模型、程序与依赖版本可能有自己的附加许可；锁文件只记录版本，不代替许可证。Windows 字体只从使用者自己的系统读取。

## 核对来源

核对日期：2026-11-10。

- [DeepTutor v1.7.1 LICENSE](https://github.com/HKUDS/DeepTutor/blob/v1.7.1/LICENSE)
- [DeepTutor v1.7.1 第三方声明](https://github.com/HKUDS/DeepTutor/blob/v1.7.1/THIRD_PARTY_NOTICES.md)
- [DeepTutor v1.7.1 贡献指南](https://github.com/HKUDS/DeepTutor/blob/v1.7.1/CONTRIBUTING.md)
- [GitHub 使用条款](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)、[可接受使用政策](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies)、[社区准则](https://docs.github.com/en/site-policy/github-terms/github-community-guidelines)
- [PyMuPDF 许可说明](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)
- [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html)
- [Jina 模型卡与许可](https://huggingface.co/jinaai/jina-embeddings-v2-base-zh)
- [RapidOCR](https://github.com/RapidAI/RapidOCR)、[ONNX Runtime](https://github.com/microsoft/onnxruntime)、[faster-whisper](https://github.com/SYSTRAN/faster-whisper)、[edge-tts](https://github.com/rany2/edge-tts)

这些记录说明本次可核查的处理措施，不代表 GitHub、DeepTutor 或其他服务方审核或背书，也不把一方的开源代码许可解释为另一方的服务账号授权。
