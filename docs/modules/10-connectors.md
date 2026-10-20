# 连接器 connectors

> 对应 Muse 设计站章节：ch09 连接器生态

## 职责
外部服务的一层适配：每个连接器只暴露 status() 与 call(action, **kwargs)。服务私有协议、限流与错误翻译都在连接器内，agent 侧只认统一契约。凭证按名向 security 索取，调用时才取。

## 对外接口
- `Connector 协议：status() / call()`
- `ConnectorStatus(name, connected, detail)`
- `ConnectorRegistry.register / get / statuses`
- `EchoConnector：无外部依赖的参考实现`

## 与谁交互、传什么
runtime/session 注册；doctor 展示全部状态；未来的工具层可把 call 包成工具。

## 数据与状态
状态与动作结果。连接是「未连接也是正常状态」：status 不抛错，call 才可能失败。

## 边界与代价
本仓库只带参考连接器。真实连接器（邮箱、日历、GitHub 等）按此契约逐个新增，每个一个模块，不互相引用。

## ADK 落地方式

连接器契约（status/call）原样保留。ADK 落地方式：连接器的能力以工具暴露——connectors/tools.py 为每个已注册连接器生成一条注册表工具 `connector_<name>`（参数 action + 可选 text），经 tools 的统一路径变成 FunctionTool，模型与普通工具无差别地调用。EchoConnector 参考实现随附，doctor 仍展示全部连接器状态。
