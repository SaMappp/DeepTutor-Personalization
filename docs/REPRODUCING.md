# 复现与维护

这些改造固定对应官方 v1.7.1，不默认适用于后续版本。先在独立源码目录复现；不要把归档中的历史部署脚本直接对准正在使用的数据目录。

## 1. 取得官方基线并检查

```powershell
git clone --branch v1.7.1 --depth 1 https://github.com/HKUDS/DeepTutor.git official-DeepTutor-v1.7.1
git -C official-DeepTutor-v1.7.1 rev-parse HEAD
```

应为 `f7aed0744c36c5afef16a4261c31ebee1208cac2`。也可从官方 tag 下载源码 ZIP。上游源码与本归档分别取得，归档不包含预编译程序或用户运行目录。

在本仓库中运行：

```powershell
python tools/verify_publication.py --upstream C:/path/to/official-DeepTutor-v1.7.1
python -m unittest discover -s tests -v
```

检查器会核对基线文件哈希，在临时目录分别应用四组补丁，并逐个核对输出与完整改造源码一致。它不会应用补丁到你提供的上游目录，也不会启动 DeepTutor。

## 2. 选择补丁目标

在另外准备的干净官方源码副本中，先用 `git apply --check`，再应用：

```powershell
# CLI/PyPI 后端方案
git apply --check C:/path/to/DeepTutor-Personalization/patches/cli-v1.7.1.patch
git apply C:/path/to/DeepTutor-Personalization/patches/cli-v1.7.1.patch

# 或桌面后端方案：在另一个干净副本执行，不能叠加在 CLI 补丁上
git apply --check C:/path/to/DeepTutor-Personalization/patches/desktop-v1.7.1.patch
git apply C:/path/to/DeepTutor-Personalization/patches/desktop-v1.7.1.patch

# 前端可与选定的后端组合
git apply C:/path/to/DeepTutor-Personalization/patches/frontend-v1.7.1.patch

# 桌面壳修改，目标仍是官方源码仓库根目录
git apply C:/path/to/DeepTutor-Personalization/patches/desktop-shell-v1.7.1.patch
```

上面两组后端命令展示不同选择，应只执行适合目标的一组。CLI 补丁含仅环回监听的启动器；桌面后端沿用桌面壳自己的监听策略。两套都包含模型推理参数和知识库阅读同步，只有桌面后端含按页 OCR。

前端快照是最后的菜单修复版；原部署记录显示该版部署到桌面前端，不能据此声称 CLI 网页也已部署最后这一版。

改造源码各自位于 `overrides/<target>/`。这也是精确查看修改后完整文件的入口。补丁已包含修改声明；不要移除原上游署名和许可。

## 3. 后端与前端构建

遵循 **v1.7.1 本身**的安装／构建说明。历史环境曾使用不同 Python 版本，Node 实际为 24.x；官方开发指南推荐 Node 22 LTS。历史依赖清单用于复现线索，不能保证未来平台仍有全部 wheel。

典型源码流程（在你选择的测试副本中）：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements/full.txt
.venv/Scripts/python.exe -m pip install -e . --no-deps
cd web
npm ci --legacy-peer-deps
npm run test:unit -- tests/chat-reasoning-selector.spec.tsx
npm run typecheck
npm run build
```

发布归档的语法／补丁检查不能代替这些应用级验证。桌面发行版还区分 runtime 中的前端资源和实际加载缓存，直接替换其中一个目录可能继续看到旧界面。历史部署脚本记录了这一点，但路径和构建 ID 不适用于其他电脑。

## 4. 学习辅助服务

按 `examples/workspace-layout.txt` 保持同级布局，复制相应 `archive/workspace/DeepTutor-learning-support/` 源码到自选位置，创建其独立虚拟环境并安装 `requirements.lock.txt`。服务的 Jina、Whisper 模型设置为只从本地读取，须另行按上游项目许可下载到预期模型缓存；仓库没有模型权重。

本地认证密钥由使用者在自己的服务目录生成，不能提交：

```powershell
python -c "from pathlib import Path; import secrets; p=Path('private/service-key.txt'); p.parent.mkdir(exist_ok=True); p.write_text(secrets.token_urlsafe(32), encoding='utf-8')"
```

`server.py` 依赖这个私有文件。检查并修改 `owner_present()` 中的本地 DeepTutor 位置；`configure_learning_services.py` 是针对原双实例的历史配置脚本，需先改成你自己的端口与设置路径。它会写入本地服务凭据并创建含凭据的私人备份，不能上传生成结果。

Edge TTS 是非微软官方 Python 客户端：联网服务可用性、访问条件和条款由服务方决定。本仓库不提供对远端服务永久免费的承诺。

## 5. 独立转换与 OCR

`archive/workspace/DeepTutor-conversion-tools/` 保存标准库转换包装器、OCR 早期实现、最终 `pdf-textbook-tool` 的 GUI／CLI／流水线及验收脚本。早期一次性脚本中的 `YOUR_NAME` 和 `authorized-source.pdf` 是脱敏占位符；优先使用最终工具的参数化入口。

PPT 转换需另装 LibreOffice 并配置脚本预期的 `LibreOffice/program/soffice.com`。PDF→图片PPT 的历史环境使用独立 Python 3.10、`pdf2pptx==1.0.5` 和 `requirements-pdf2pptx.lock.txt`；不要把旧环境依赖混装进 DeepTutor 主环境。

最终 OCR 工具使用 `rapidocr-onnxruntime==1.2.3`、PP-OCRv3 中英文识别模型、ONNX Runtime、PyMuPDF、NumPy、httpx、pypdf；引擎还从 Windows 读取 `msyh.ttc`，该字体不随仓库分发。按 `engine.py` 的 `RUNTIME` 约定将 OCR 包及模型放到 `ocr/runtime`。该目录可用 pip 的 `--target` 单独安装；其他依赖放在工具自己的虚拟环境。也可在明确理解导入次序后适配已有环境。

```powershell
python -m pip install --target ocr/runtime rapidocr-onnxruntime==1.2.3 opencv-python-headless pyclipper shapely
python pdf-textbook-tool/cli.py --help
python pdf-textbook-tool/gui.py
```

这两条入口需由安装了 PyMuPDF、ONNX Runtime 等依赖的 Python 执行。仓库不捆绑依赖，不把历史机器上的依赖组合宣称为全平台锁文件。先用自己创建或获授权的样例 PDF 验证。

## 6. 原生按页 OCR 的配置

将 `examples/native-ocr.configuration.example.json` 复制到自己的私有配置位置，设置 `python`、`worker`、`tool_root`、缓存目录和根目录。`worker.py` 取自 `archive/workspace/DeepTutor-native-ocr/`，工具引擎来自上节最终工具。

用选定解释器导入 `pdf-textbook-tool/engine.py` 并调用 `descriptor()`，将所得引擎描述写入配置的 `engine`。它会校验模型、运行库和本机字体哈希；示例中的哈希来自原开发环境，不能假装在别的电脑仍匹配。此操作不运行 OCR。

```powershell
$env:DEEPTUTOR_NATIVE_OCR_CONFIG='C:/your/private/native-ocr/configuration.json'
```

在启动选定桌面后端的环境里设置该变量。公开版 `native_ocr.py` 读取它；未设置时默认查找用户目录下的 `DeepTutor-native-ocr/configuration.json`。worker 仍从自身目录读取 `configuration.json`，因此将实际配置放在 worker 旁边，或保持两份配置一致。

单页扫描文档、并发和缓存测试应使用自己的合成样例。历史验收程序含原测试目录假设，原测试 PDF 未分发；不能运行后声称自动具备所有历史材料。

## 7. 模型、数据与升级

首次配置由用户自己通过官方登录或获准 API 完成。`tools/provider_config.py` 默认只读检查；显式 `--apply` 才增量写入模型 profile，不更改活动默认模型。详见 `PROVIDER_INTEGRATIONS.md`。

同一运行目录的网页与 CLI 不同时持有学习请求；需要切换时先确认 `/api/system/runtime` 的 `owner_turn_count=0`，再仅停止归属明确的服务。桌面和 CLI 使用不同运行目录；不要合并数据库或复制登录凭据。

升级可能覆盖 site-packages、桌面 runtime 和缓存中的补丁。先保留私人备份，在新版本源码重做差异检查及功能验证，再决定迁移；不要强行把旧补丁覆盖到版本不同的程序上。
