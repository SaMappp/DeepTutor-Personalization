> 历史记录脱敏副本：其中“当前”“已验证”仅指原记录时点；操作路径已替换。公开版以仓库 README 和复现说明为准。

# DeepWorks 模型接入说明

已配置并验证：2026-11-05。

DeepTutor 的 PyPI/CLI 版与 Windows 桌面版均已新增“DeepWorks 积分（DeepFoundry）”提供商，按照 2026-11-06 的用户指令，默认固定为 GPT-6.1-Sol / high。DeepWorks 模型仍为可选来源，同步不会修改默认模型。原 OpenAI Codex 登录、gpt-6.1-sol 的 high 配置、聊天和学习资料均保留。

## 已导入的 9 个模型

- DeepSeek-V4-Flash
- DeepSeek-V4-Pro
- DeepSeek-V4.1-Flash
- GLM-5.3
- GLM-5.3-Flash
- Kimi-K3
- Kimi-K3.1-Pro
- Qwen-3.8-Max
- Deepexi-E-Pro-2.0

模型名称、上下文与能力信息来自你当前 DeepWorks 的实际模型配置，并与它正在使用的网关模型目录交叉核对。Auto、语音、图像生成、文档解析和 embedding 模型没有混入聊天列表。此次没有更换知识库的 embedding 配置。

## 如何使用

桌面版：双击桌面“Open DeepTutor”。在聊天输入框附近点击模型名称，即可选择标有“DeepWorks 积分（DeepFoundry）”的模型；也可以切回 OpenAI Codex。已有聊天可能保留它自己的模型选择，新聊天默认使用 GPT-6.1-Sol。关闭桌面窗口即可退出桌面 App。

Codex App：例如输入“用 DeepTutor 给我讲解导数，并出三道中文练习题”，也可明确写“使用 $deeptutor-cli”。本机 skill 已更新为遵循当前 DeepTutor catalog 的模型选择，不会强制切回 Codex 或自动改用其他计费来源。CLI 使用原 PyPI 数据；桌面 App 使用独立数据，聊天和学习资料不互相同步。

## 积分与连接方式

本次复用 DeepWorks 自身生成的 DTH 专用模型 API Key，通过 OpenAI Chat Completions 兼容协议直连：

https://tokenhub.deepexios.cn/gateway/api/v1

已在内存中核对：写入 DeepTutor 的凭据与当前 DeepWorks 登录记录中的模型凭据一致。当前身份为企业成员、组织空间，因此接入的是当前企业空间的模型通道；不是另行连接的 tjusz 校园接口，也没有新建付费 API 账号。

实际模型请求和 token 用量已验证。没有取得逐笔积分扣费流水，因此不报告具体消耗多少积分；实际积分结算请查看 DeepWorks 的用量明细。DeepTutor 界面中的美元成本属于其自身估算，不能当作 DeepWorks 的结算账单。

DeepTutor 官方支持自定义 OpenAI 兼容 API；DeepWorks 面向普通用户的公开文档没有给出稳定的外部客户端授权流程。本次连接复用了当前版本已有的专用模型配置，不是 DeepTutor 官方内置的 DeepWorks OAuth 连接器。平台升级、凭据轮换或接口规则变化后可能需要重新同步。

## 密钥更新后如何恢复

DeepWorks 重新登录、切换账号/企业空间或轮换凭据后：

1. 在 DeepWorks 中确认已登录到你希望使用的空间。
2. 打开 DeepTutor 桌面版，并运行本文件夹中的 Start-DeepTutor.cmd 打开 PyPI 服务。
3. 等待两套 DeepTutor 的学习请求完成。
4. 双击 Sync-DeepWorks.cmd。它会重新核对网关与模型，更新两套 DeepTutor 的专用凭据，保留当前默认选择和其他提供商。
5. 如果网页已经打开但列表仍旧，刷新页面或重新打开桌面 App。

同步脚本不包含密钥，也不会显示密钥。不变的配置不会重复保存；发生变更时会先在各自 data/user/settings/backups 中备份模型 catalog。日常请求由 DeepTutor 直接访问模型网关；同步更新时需要 DeepWorks 已有有效登录。

## 验证记录

- 官方网关返回模型目录；DeepSeek-V4-Flash 的短中文请求成功。
- CLI 实际完成“解释导数、计算 f(x)=x² 在 x=3 处的导数、出一道练习”，返回 completed 和 done；模型为 DeepSeek-V4-Flash。
  会话：SESSION_ID
  本地记录：verification/deepworks-cli.jsonl
- 桌面版后端对应的完整前端可选择全部 9 个模型。GLM-5.3-Flash 完成了矩阵秩的中文解释、秩为 1 的矩阵例子及练习。
  会话：SESSION_ID
  本地记录：verification/deepworks-desktop.txt
- GLM 首次请求遇到 TLS 连接超时；核对网络恢复后，一次重试完成。未关闭 TLS 证书校验，也未修改系统代理。
- 已正常关闭并通过原桌面图标重新启动桌面 App。重启后，两套后端均 ready，默认模型与 9 个模型条目仍在，GLM 测试会话仍为 completed。
- 原 Codex profile 保留。同步脚本重复运行验证为 unchanged，没有重复添加模型。
- 服务仍仅监听 127.0.0.1：PyPI 使用 8001/3782，桌面版使用 18801/18802。未设置开机自启，未创建“线代教学”目录。
- 本次实际验证了 DeepSeek-V4-Flash 和 GLM-5.3-Flash；其余模型已核对目录与导入，未逐一产生付费推理请求。

## 依据

- DeepTutor 官方提供商配置：https://docs.deeptutor.info/zh-cn/get-started/providers/
- DeepWorks 官方积分规则：https://deepworks.cn/deepworks-docs/billing/credits/
- DeepWorks 官方用量查询：https://deepworks.cn/deepworks-docs/billing/usage/
- 原始开发者公开接入资料（历史版本，作为线索）：https://github.com/SHYXIN/skills/blob/f8d57b9abc4520f5436655d28c5c6b52f034a790/skills/company/dp-dth-key-setup/SKILL.md

实际网关与凭据取自当前安装的 DeepWorks 1.5.0；没有照搬历史资料中的 test/prod 网关地址，也没有安装其中面向 pi 的脚本。
