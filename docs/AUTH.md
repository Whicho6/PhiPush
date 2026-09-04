# TapTap 与 Phigros 云存档认证

PhiPush 只读取当前用户本人明确授权后的数据。项目没有上传、改分或作弊接口。

## TapTap device-code 流程

Web 登录流程如下：

1. 后端向 TapTap 请求 device code 与二维码地址。
2. Web 展示二维码、授权链接和剩余有效时间。
3. 用户使用 TapTap 扫码并确认。
4. 后端按服务端给出的间隔轮询授权状态。
5. 授权成功后，后端使用 MAC 凭证读取当前 TapTap 用户资料。
6. 后端通过 Phigros 使用的 LeanCloud 身份流程换取 SessionToken。

二维码过期、网络失败和授权失败会作为不同状态返回。该流程依赖第三方服务当前行为，不是面向 PhiPush 保证稳定的官方公共 API。

## 云存档只读流程

取得 SessionToken 后，后端：

1. 读取当前 LeanCloud 用户信息。
2. 查询最新 `_GameSave`。
3. 下载云存档 ZIP。
4. 读取并解密 `gameRecord`。
5. 解析成绩并与本地曲库标准化。
6. 计算 RKS、P/B 槽位和推分建议。
7. 创建随机短期 PhiPush 会话，并结束真实凭证的使用。

所有上游操作均为读取。代码没有云存档上传或成绩修改路径。

## SessionToken fallback

Web 提供手动 SessionToken fallback，主要用于 TapTap device-code 暂时不可用的情况。Token 仅发送给本地后端，并进入同一个只读云存档加载流程。不要通过 Issue、截图、聊天或日志分享 SessionToken。

## 敏感凭证处理

- 不把 SessionToken 写入数据库、普通 JSON、缓存文件或应用日志
- 前端不回显完整 SessionToken
- 云存档读取完成后尽快清除局部凭证引用
- 返回给前端的是随机 PhiPush 会话 ID，不是真实 Phigros 凭证
- 会话默认 15 分钟过期，服务重启后立即失效
- `.env`、本地曲库和常见秘密目录由 Git 忽略

Python 运行时不保证字符串能被立即从物理内存擦除。若部署到非个人本机环境，还必须禁用请求体日志、使用 HTTPS、限制访问来源，并采用适合该环境的密钥管理和隔离措施。

## 真实账号验证范围

作者曾使用本人账号完成一次端到端验证，包括：

- TapTap 扫码授权
- 本人玩家信息与云存档读取
- gameRecord 解析
- RKS 与游戏内显示核对
- P1–P3/B1–B27 与单曲成绩核对
- 基于真实成绩生成推分推荐

公开仓库不包含该账号的昵称、标识、Token、Cookie、真实成绩或私人存档。这次验证只说明当时的作者账号链路可用，不代表所有账号、地区、游戏版本或未来服务状态。

## 非官方协议风险

PhiPush 与 Phigros、Pigeon Games、TapTap、WeChat 没有官方隶属、合作、授权或背书关系。TapTap、LeanCloud、Phigros 云存档格式、加密参数和接口均可能变化。公开运营还需要单独确认平台许可、隐私合规、请求限额和部署安全；本仓库不声称已经取得公开服务授权。
