> 历史记录脱敏副本：其中“当前”“已验证”仅指原记录时点；操作路径已替换。公开版以仓库 README 和复现说明为准。

# DeepSeek 账号余额与聊天推理强度

已配置：2026-11-06。默认模型固定为 GPT-6.1-Sol / high；导入、同步和临时验证其他模型均不修改默认值。

## 模型来源

桌面版与 PyPI/CLI 版均保留以下三个独立来源：

| 列表中的来源 | 模型与计费 |
| --- | --- |
| OpenAI Codex | GPT-6.1-Sol 等，使用原有订阅登录；默认 GPT-6.1-Sol |
| DeepWorks 积分（DeepFoundry） | 原有 9 个模型，使用当前 DeepWorks 企业空间的积分通道 |
| DeepSeek 账号余额（Harness） | 新增 DeepSeek-V4.1-Flash、DeepSeek-V4-Pro，使用现有 DeepSeek 账号的充值/赠送余额 |

新增模型的实际 API ID 分别是 deepseek-flash、deepseek-v4-pro。菜单每行会显示来源，避免将同名 Pro/Flash 的两种计费渠道混淆。

本次直接复用当前 DeepSeek Harness 账号授权，没有创建或要求你提供额外 API Key。模型目录和实际请求都发往 DeepSeek 官方 api.deepseek.com。已核对它与 Harness 的 platform.deepseek.com 人民币钱包为同一账号；钱包查询使用了同一授权。验证期间观察到的钱包变化已保存在 verification/deepseek-account-wallet-check.json；它包含同账号同期所有请求的变化，不冒充逐笔账单。

## 聊天中修改推理强度

在聊天输入框右侧，模型选择图标旁新增了脑形图标和当前强度（例如“高”）。

1. 先选需要的模型。
2. 点击脑形图标/强度名称。
3. 选择支持的等级。保存完成后，下一条消息使用新设置。

GPT-6.1-Sol 的菜单来自当前订阅模型目录；DeepSeek 账号模型提供自动、low、high、max；DeepWorks 模型按其实际目录提供各自支持的等级。

修改的是该模型已保存的强度，会影响随后使用该模型的对话。它不会切换全局默认模型，也不会改动其他模型的强度。正在生成或正在保存强度时会锁定相关操作；保存失败会保留原值并显示“保存失败”，可重试。空白聊天页的菜单向下展开，有消息/停靠的输入区向上展开，避免遮挡。

## Codex 中使用

直接说“用 DeepTutor 给我讲解导数并出三道题”，默认仍用 GPT-6.1-Sol。

如果明确指定其他来源，使用该来源的会话模型选择，不修改全局默认模型。CLI 的 --session 会沿用已有会话的模型选择，本次已实际验证它沿用 DeepSeek Pro 完成中文追问。本机 deeptutor-cli skill 已保存默认模型规则和两个同步入口。

## 登录授权变化后

在 Harness 重新登录或授权失效后，打开两套 DeepTutor，等待当前学习请求结束，再运行本文件夹中的 Sync-DeepSeek-Account.cmd。它读取当前 Harness 的有效授权，更新两套 DeepTutor，保留默认模型及其他提供商。

DeepWorks 的凭据变化仍使用 Sync-DeepWorks.cmd；该脚本已经移除了修改默认模型的选项。

不要将账号令牌或模型密钥发到聊天。两个同步脚本本身均不包含实际凭据，也不会打印凭据。

## 数据与本地补丁

聊天和学习数据保持原目录；桌面版和 PyPI/CLI 的数据仍各自独立。服务只监听 127.0.0.1，没有设置开机自启，也没有创建“线代教学”目录。

推理强度按钮属于此次安装的本地补丁，基于与当前运行时相同的官方 v1.7.1（f7aed0744）。可编辑源码在 Academic learning/DeepTutor-local-ui，本地分支为 codex/chat-reasoning-control。未更换后端版本。

原前端、运行缓存与后端单文件均保留了 before-reasoning 时间戳备份；具体位置记录于 verification/reasoning-ui-deployment*.json。回退只涉及这些程序文件和缓存，不涉及模型配置、登录、聊天或学习数据。升级/重装 DeepTutor 可能覆盖界面补丁，届时需要按新版本重新应用。

## 验证

- Flash：桌面版后端对应的完整界面完成了中文导数讲解和出题。
  会话 SESSION_ID。
- Pro：PyPI 完整界面完成中文线性相关讲解；CLI 随后沿用该会话完成中文追问，结果记录明确为 deepseek-v4-pro。
  会话 SESSION_ID。
- 聊天界面实测修改 GPT 强度并恢复 high；两套安装的全局默认均保持 GPT-6.1-Sol。
- 7 项控件回归测试通过；定向 ESLint、完整 TypeScript 检查与生产构建通过。
- 模拟保存延迟时，立即按回车不会启动学习请求，草稿仍保留，发送与切换模型暂时禁用；延迟测试已移除。
- 已检查正常窗口和窄窗口下的新按钮布局。测试中的账号模型强度均恢复为原来的 high。
- 验证记录保存在 verification/deepseek-account-*.txt / .jsonl 及 reasoning-control-*.png。

## 官方依据

- Harness 账号通道：https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/llm/llm-deepseek-account/README.md
- Harness 账号认证与接口：https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/llm/llm-deepseek/README.md
- DeepSeek 当前模型与余额扣费规则：https://api-docs.deepseek.com/quick_start/pricing/
- DeepSeek 推理强度参数：https://api-docs.deepseek.com/guides/thinking_mode/
