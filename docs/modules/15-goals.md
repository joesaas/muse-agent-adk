# 目标与跟踪 goals

> 对应 Muse 设计站章节：ch18 Goals 与 Ideas

## 职责
把「耐久目标」和「具体承诺」做成数据而不是聊天记录：目标（active/completed）与跟踪项（open/completed）存一个 JSON 文件，每次会话都能读回，不随对话滚动丢失。

## 对外接口
- `GoalTracker.add_goal / add_item / complete_item / open_items`
- `Goal / TrackedItem 数据类`

## 与谁交互、传什么
runtime/session 在组装时创建；CLI doctor 显示计数。

## 数据与状态
home/goals.json。字段刻意少，流程状态机以后在这一层扩展，不散落到对话里。

## 边界与代价
这里只管「记什么状态」，不管提醒与催办——那是 scheduling 与主动性策略的事，分层别混。

## ADK 落地方式

本模块无 ADK 接点：GoalTracker 与 goals.json 格式原样保留，session 组装时创建，doctor 显示计数。它只管状态数据，不管提醒与催办（那是 scheduling 与产品层的事），分层与原版一致。
