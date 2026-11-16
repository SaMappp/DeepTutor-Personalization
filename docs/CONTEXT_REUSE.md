# 上下文调查复用

适用：DeepTutor v1.7.1 桌面后端。官方原流程对含文字来源的聊天每轮先运行一次模型调查，再进入回答；历史附件仍会触发该阶段。

本改动在首次、新增或改变资料时保留官方调查。在同一账号、工作区、会话、分支和资料版本的后续问题中复用历史调查，不增加额外模型分类调用；回答模型仍能用 `read_source` 核对原文、补查新细节。复用提示明确标注原问题范围，并保持第三方对话的身份和指令隔离。

缓存位于账号私有 `.runtime/context-investigations.sqlite3`，最多 128 条、每条摘要最多 64,000 字符；只存摘要、截短的原问题及校验身份，不复制原始来源或图片。来源全文哈希、语言和模型参与键计算；条目只可由祖先消息使用。缓存缺失、不可用或分支身份不足时回退官方流程。旧会话安装本补丁后可能仍需一次调查建立缓存。Mastery 保留原有来源工具绑定和权限门控。

完整源码在 `overrides/desktop/deeptutor/` 的 `capabilities/explore_context/{capability,reuse}.py`、`agents/loop/pipeline.py`、`services/session/turns/executor.py`。四文件已并入 `patches/desktop-v1.7.1.patch`，使用方式见 [复现说明](REPRODUCING.md)。

无需 DeepTutor 环境的缓存回归由默认测试发现命令运行。额外 14 项能力/工具集成检查需要现有 v1.7.1 依赖：

```powershell
$env:DEEPTUTOR_CORE = 'C:/path/to/installed/v1.7.1/core'
python tools/check_context_reuse.py
```

检查器使用合成身份和内容、模拟前置调查，实际运行来源读取工具与工具挂载逻辑；不发出模型请求。`archive/workspace/DeepTutor-context-reuse/` 保存参数化后的部署与真实合成对话脚本；使用者须显式设置 `DEEPTUTOR_CORE` 和 `DEEPTUTOR_WORKSPACE_ID`。它们会操作指定的本机服务，应先阅读源码；脚本生成的私有状态不能提交。

本机历史验证通过 14 项离线回归及两轮真实合成文本对话；第二轮没有 `context_exploration`，实际读取原文并答对新细节。两轮约 13.887 秒与 9.220 秒，只证明行为路径，不能作为长文档或其他机器的速度预测。此次公开脚本经过路径/标识参数化，未再次向真实学习会话发送消息。
