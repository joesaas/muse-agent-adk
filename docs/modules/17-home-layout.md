# 家目录 home

> 对应 Muse 设计站章节：ch10 文件架构 / ch14 页面交互与多端

## 职责
agent 的一切所知都放在用户拥有的一个目录里（默认 ~/.muse-agent）：站立文件、记忆、skills、会话快照、目标数据、配置。初始化只补缺、永不覆盖用户文件。

## 对外接口
- `ensure_home(home) -> 新建文件列表`
- `HOME_FILES 模板表`

## 与谁交互、传什么
runtime/session 启动时调用；其余模块都从这里拿路径，不各自发明位置。

## 数据与状态
目录即数据格式：全是可读文本（md/json/toml），用户可直接查看、编辑、备份、迁移。

## 边界与代价
多端不靠同步这个目录的设计来解决：各端连同一运行时或同一 home 的托管副本；前端只是入口，不是状态所在地。

## ADK 落地方式

布局与模板原样保留，仅默认目录改名 `~/.muse-agent-adk`（环境变量 `MUSE_AGENT_ADK_HOME`），以便与原版并存。文件格式（站立文件、MEMORY.md、memory/ 每日笔记、skills/、sessions/ 快照、goals.json、config.toml）与原项目逐项兼容：同一个 home 在两个项目间可读。ensure_home 仍是只补缺、永不覆盖。
