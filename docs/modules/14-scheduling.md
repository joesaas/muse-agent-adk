# 定时与后台 scheduling

> 对应 Muse 设计站章节：ch11 定时与后台

## 职责
两种唤醒机制：cron（时间驱动，5 段表达式 + prompt + 目标）与 hooks（条件驱动，轮询 check()、命中即唤醒）。两者只发事件，不直接调 LLM——智能只发生在被唤醒的 agent run 里。

## 对外接口
- `CronSpec(expr).matches(datetime)`
- `Scheduler.add(Job) / tick(now) -> 到期 Job 列表（同分钟去重）`
- `HookRegistry.register(name, check) / poll() / reset(name)`
- 事件：cron.due / hook.fired

## 与谁交互、传什么
宿主进程决定 tick 频率（通常每分钟）；EventBus 把到期事件交给 runtime。

## 数据与状态
Job 是数据：id、spec、prompt、enabled、last_run_minute。prompt 是立项时记录的请求原文，运行时照它执行，不临场改写范围。

## 边界与代价
调度器不睡觉、不执行：它只是判定者。错过的时间不补跑（除非宿主另行实现），这一点要在产品层面对用户讲清。

## ADK 落地方式

本模块与原版逐字一致：CronSpec/Scheduler/HookRegistry 只判定、只发事件（cron.due / hook.fired），不托管进程、不直接调模型。ADK 侧的接法不变：宿主把事件翻译成一轮 `Agent.run_turn(prompt)` 即可，智能只发生在被唤醒的 run 里。托管 tick 循环仍留待宿主或后续阶段，与原版边界相同。
