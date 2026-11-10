> 历史记录脱敏副本：其中“当前”“已验证”仅指原记录时点；操作路径已替换。公开版以仓库 README 和复现说明为准。

# DeepTutor：Codex 与 Windows 桌面版

## 在 Codex 中使用

官方 CLI skill 已安装在 `C:\Users\YOUR_NAME\.codex\skills\deeptutor-cli\SKILL.md`，官方内容基于 DeepTutor v1.7.1，文件末尾附有这台电脑的路径与并发使用说明。新一轮对话可直接说：

- “用 DeepTutor 给我用中文讲解矩阵的秩。”
- “用 DeepTutor 分步骤解这道线性代数题。”
- “用 DeepTutor 给我出五道 Python 函数练习题，并解释答案。”

Skill 使用原有 PyPI 安装 `C:\Users\YOUR_NAME\Documents\ChatGPT\Academic learning\DeepTutor`，保留原有登录、配置和学习数据。网页服务如果使用该目录，skill 应先确认没有进行中的任务，再停止该服务、调用 CLI，并在完成后恢复服务；独立桌面版使用另一份数据，可同时运行。

实际验证：新的 Codex 测试会话自动识别并读取了 skill，也尝试了正确的 CLI 命令；非交互测试沙箱拒绝写入现有 DeepTutor 日志，因此该会话未取得 DeepTutor 答案。随后在本会话按单条命令申请权限，实际使用现有订阅调用 CLI，收到了完整中文回答。Codex 的实际权限取决于聊天的权限模式；如果提示，只为具体的 DeepTutor 命令授予必要权限。没有关闭沙箱或改变全局权限配置。

自动审批拒绝了一个为整个独立 Codex 会话授予数据目录和网络广泛权限的验证方案，理由是超出单次验证所需范围；没有采用该方案。逐条审批的非交互 Codex 测试也未能发起权限请求，因此“新 Codex 会话自动执行完整调用”仍需在可进行单次权限批准的会话中复测。

## 打开、关闭桌面版

双击桌面的 `Open DeepTutor` 图标。应用文件是 `C:\Users\YOUR_NAME\Documents\ChatGPT\Academic learning\Open DeepTutor-win32-x64\Open DeepTutor.exe`。关闭桌面窗口即可退出，并停止它自行启动的服务。

官方 Windows 便携包来自 https://github.com/HKUDS/DeepTutor/releases/tag/v1.7.1 ；下载包 SHA-256 与该官方 Release 公布的值一致。桌面版是官方预览版，Windows 程序未做 Authenticode 签名。

桌面版已单独用同一个 ChatGPT/Codex 订阅完成 OAuth 登录；当前模型为 gpt-6.1-sol、推理强度 high，界面和回答为中文。已通过桌面窗口实际发送中文问题、收到回答，并验证关闭和通过桌面图标重新打开。重启后登录与测试对话保留。临时调试端口已关闭。

## 两份数据

- Codex CLI 与原 PyPI 网页：`C:\Users\YOUR_NAME\Documents\ChatGPT\Academic learning\DeepTutor\data`，共享原有设置和学习数据。
- 官方桌面 App：`C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\workspace\data`，其设置、登录凭据、聊天和学习数据独立，不会自动同步。

桌面 App 的独立数据位置是该版本官方默认路径；没有使用测试环境变量或链接强制共享。两个服务端口均绑定 127.0.0.1，未设置开机自启。原服务端口 8001/3782，桌面版通常使用 18801/18802（若端口占用会选择可用端口）。