# PhiPush 架构

PhiPush 是一个本地优先的 FastAPI 应用。当前经过实际验证的是 Web 入口；微信小程序目录是复用同一 API 的未完成原型。

## 组件

```text
Web / 微信小程序原型
          │
          ▼
       FastAPI
          │
     短期内存会话
          │
   Record Normalization
          │
   RKS Engine → Push Planner
```

### FastAPI

`app/main.py` 创建应用、挂载静态文件与模板、加载谱面数据，并注册统一 JSON API。真实模式缺少完整曲库时会以 degraded 状态启动，真实认证入口返回 503；Mock 模式使用仓库内的演示数据。

### Web

Web 由 Jinja2 模板和原生 HTML/CSS/JavaScript 组成，不需要单独的前端构建步骤。它是当前完成本地与真实账号验证的入口。

### 微信小程序

`miniprogram/` 使用 `wx.request` 调用相同 API，但目前仍使用 `touristappid` 与 localhost 示例配置，尚未完成登录中间状态、正式 AppID、HTTPS 域名、开发者工具和真机验证。

### Session store

`MemorySessions` 使用随机短期会话 ID 在进程内保存标准化后的玩家数据，默认 TTL 为 900 秒。服务重启后全部会话消失；该实现不适合多实例共享状态。

### Record normalization

云存档解析结果与 Mock 数据都会转换成统一的 `PlayerData` / `Record` 结构。未知谱面保留记录但标记为不可计算，避免影响其他成绩。

### RKS Engine

`app/services/rks.py` 负责单谱 RKS、P1–P3/B1–B27、cutoff、目标 ACC 反推和单次成绩变化模拟。

### Push Planner

`app/services/push_planner.py` 生成候选 ACC、估算总 RKS 增益、计算推荐分数，并用逐步重算的贪心方法生成目标路线。

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | 模式、曲库和 TapTap 配置状态 |
| POST | `/api/auth/mock` | Mock 模式创建演示会话 |
| POST | `/api/auth/taptap/start` | 创建 TapTap device-code 登录 |
| GET | `/api/auth/taptap/status/{login_id}` | 查询扫码登录状态 |
| POST | `/api/auth/session-token` | SessionToken fallback |
| GET | `/api/player/summary` | 玩家概览与当前 RKS |
| GET | `/api/player/records` | 全部标准化成绩 |
| GET | `/api/player/best` | P1–P3/B1–B27 排名 |
| POST | `/api/analysis/opportunities` | 推分机会 |
| POST | `/api/analysis/target-route` | 目标 RKS 路线 |

交互式 OpenAPI 文档位于 `/api/docs`。

## 本地与公开部署

默认配置面向 `127.0.0.1` 的单机使用。公开服务还需要 HTTPS、可信的配置管理、请求体日志控制、CORS、限流、隐私合规以及第三方服务许可；当前仓库不声称已完成这些工作。
