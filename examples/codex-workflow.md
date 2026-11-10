# Codex 调用 DeepTutor 的本地工作流示例

这是本机 CLI skill 个性化说明的公共化版本，供使用者适配自己的目录；不是 Codex 账号配置或授权导出。

- 固定使用已有的 DeepTutor 安装和 `DEEPTUTOR_HOME`，不在当前聊天目录临时重新初始化。
- 用安装自身的 `.venv/Scripts/deeptutor.exe`，先查看对应版本的 `--help`，再选 chat、deep_solve 或 deep_question。
- 课程问题显式传入该实例的 `--workspace` 和 `--kb`，每次追问仍带范围，不通过改变全局默认工作区切换科目。
- 保持用户选择的全局模型及推理强度。其他来源只用于明确指定的会话；模型来源和计费渠道分别标记。
- 同一运行目录的网页与 CLI 不同时持有学习请求。通过本机 runtime 接口确认无活动任务后，只停止归属明确的 PyPI 网页服务；完成 CLI 后恢复原先运行状态。
- 独立桌面版使用自己的运行目录、授权和数据，不与 CLI 强制合并。
- 需要知识库、转写或朗读时，先准备用户已配置的学习辅助服务；不打印本地认证密钥。
- 中文教学保留必要英文术语，引用真实检索资料及页码。检查结果和 `done/completed` 事件，不把脚本启动成功当作回答完成。
- 遇到沙箱限制时只请求具体 CLI 调用所需的权限；不要关闭全局沙箱。没有拿到 DeepTutor 结果时应如实说明。

```powershell
$env:DEEPTUTOR_HOME='C:/your/DeepTutor'
$env:PYTHONUTF8='1'
& "$env:DEEPTUTOR_HOME/.venv/Scripts/deeptutor.exe" run chat '请用中文逐步讲解这个概念。' --language zh --format json
```

运行前应完成上述并发与授权检查。示例不提供任何账号凭据、个人工作区 ID、知识库名称或学习记录。
