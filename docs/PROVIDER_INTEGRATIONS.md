# 模型来源与公开版接入

原环境将 Codex 订阅、DeepWorks 企业积分、DeepSeek 账号余额分开标记，解决同名模型看不出计费来源的问题。默认仍为当时选定的 GPT-6.1-Sol/high；这是维护者的历史偏好，其他人的订阅、可用模型和价格需要自己确认。

## 历史实现与公开版差异

| 来源 | 原环境的做法 | 公开内容 |
|---|---|---|
| Codex | DeepTutor 原生 OAuth，各实例分别登录 | 使用流程；不含任何登录状态 |
| DeepWorks | 从已登录客户端的当前配置取得模型专用凭据，核对模型目录后增量导入 | 接入经历、来源区分和默认保留设计；自动读取客户端凭据的原脚本及启动入口留在本机 |
| DeepSeek Harness | 使用账号模型目录和账号授权头，固定官方目的地、拒绝重定向 | 历史适配器公开版改为显式环境变量授权；不读取原凭据文件、不发布钱包查询或账号数据 |
| 通用 API | 整理发布时新增 | `tools/provider_config.py`，仅由使用者显式提供 endpoint、模型和凭据环境变量 |

DeepWorks 的原说明未能提供稳定、公开的第三方客户端授权流程；代码开源也不构成服务方授权。维护者明确选择不公开自动提取部分。历史账号接入不代表官方集成、永久有效，或可把登录令牌用于任意客户端。

[DeepSeek Harness 官方账号参考](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/llm/llm-deepseek-account/README.md) 描述账号目录、目的地验证和 `x-dsh-auth-token`；本仓库不绕过登录、账号资格或模型准入。原版本的手动适配并未实现 Harness 全部生命周期与模型准入机制，只作为历史参考。

## 通用公开工具

复制 `examples/provider.example.json` 为自己 **不提交** 的 `provider.private.json`，填入合法获准使用的 HTTPS endpoint、确切模型 ID、目标本机端口及私有设置目录。凭据只通过 `api_key_env` 所指进程环境变量传入；配置文件不放实际密钥。

```powershell
# 在你自己的终端安全设置 DEEPTUTOR_PROVIDER_API_KEY 后：
python tools/provider_config.py provider.private.json
python tools/provider_config.py provider.private.json --apply
```

第一条仅检查本机服务和配置，不发送远端模型推理请求、不写设置；第二条预检目标无活动任务后备份 catalog，按 `activate: false` 导入。脚本核对默认 profile/model 未变，异常时只打印异常类型。多目标应用不是跨实例事务，某个后续目标失败时，之前成功的目标不会自动回滚。

工具不扫描 DeepWorks、Harness 或 Codex 的登录目录，不创建新账号，不推断模型权限，也不声称已验证未调用过的模型。备份包含原 catalog 中的凭据，应保留在私人设置目录，不能提交 GitHub。

历史推理强度 UI 与这些授权方式独立：前端按 profile/model 声明的等级保存，后端按官方 v1.7.1 的请求映射机制发出参数。没有更改原服务计费规则。
