---
id: intro
title: APICred 文档总览
slug: /
---

欢迎来到 APICred 文档站。

如果你是首次使用 APICred，建议按下面顺序阅读：

1. USAGE：用户侧完整流程（登录、模型、Token、OpenAI SDK 调用）
2. SDK：Python SDK 与 OpenAI SDK 的调用方式
3. BASALTPASS_QUICKSTART：与 BasaltPass 的本地联调

## 当前版本关键说明

- 用户侧默认只支持 BasaltPass SSO 登录。
- 本地注册/密码登录在生产与常规环境默认关闭。
- 聊天接口兼容 OpenAI Chat Completions 形态：`POST /v1/chat/completions`。
- 计费链路统一通过 BasaltPass，Stripe webhook 在 APICred 侧已禁用。

## 常用入口

- 前端控制台：`http://localhost:5106`
- 后端健康检查：`http://localhost:8103/health`
- API 基础路径：`http://localhost:8103/v1`

## 谁该看哪份文档

- 普通用户 / API 调用方：USAGE、SDK
- 运维 / 上线同学：DEPLOYMENT、PRODUCTION
- 后端开发：DEVELOPMENT、TESTING