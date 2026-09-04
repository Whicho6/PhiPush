# PhiPush

> What should I grind next?

PhiPush 是一个面向 Phigros 玩家的 RKS 推分规划工具。它读取玩家本人授权的成绩后，不只展示 B30，还会模拟不同谱面的 ACC 提升，估算其对总 RKS 的贡献，推荐下一张更值得推的谱面，并规划目标 RKS 的近似路线。

## 当前状态

✅ Web 本地版已验证<br>
✅ TapTap 真实账号登录与云存档读取已完成一次端到端验证<br>
✅ RKS / B30 / Phi 计算已与真实账号结果核对<br>
✅ 推分推荐与目标 RKS 路线<br>
🚧 微信小程序原型，尚未完成真机或正式环境验证<br>
🚧 尚未作为公共在线服务部署

> **非官方声明：** PhiPush 是非官方第三方社区项目，与 Phigros、Pigeon Games、TapTap、WeChat（微信）没有官方隶属、合作、授权或背书关系。真实登录只代表作者本人在一个账号和当时版本上的一次端到端验证，不代表所有账号或后续版本；第三方接口和协议未来可能变化。

## Demo

![PhiPush Mock Dashboard](docs/images/dashboard-mock.png)

截图由 Mock 模式生成，仅包含仓库内的虚构玩家和虚构成绩，不含真实账号、昵称、Token、Cookie 或云存档数据。

## 核心功能

- 显示当前 RKS、P1–P3、B1–B27、入选线和全部谱面成绩
- 按 ACC、定数或单谱 RKS 搜索、筛选和排序
- 模拟多个 ACC 目标，估算 B27 与 Phi 槽的总 RKS 收益
- 输出 Top 10 推分机会及推荐理由
- 为目标 RKS 生成最多 10 步的近似路线
- 遇到未知谱面时安全降级，不因缺少定数而崩溃
- 只读访问云存档，不包含上传、改分或作弊功能

## 快速开始

需要 Python 3.11+：

```bash
git clone <your-repository-url>
cd PhiPush
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
```

### Mock 模式

```bash
python run.py --mock
```

打开 `http://127.0.0.1:8000`，点击“进入 Mock 演示”。Mock 模式使用 42 条虚构成绩，不需要 TapTap 账号、真实凭证或完整曲库。

### Real 模式

```bash
python run.py
```

真实模式需要在本地提供以下配置，示例见 [`.env.example`](.env.example)：

- TapTap / Phigros 客户端配置
- LeanCloud 应用配置
- gameRecord AES 参数
- 完整本地曲库 `data/charts.json`，或 `PHIPUSH_CHART_DATA` 指向的数据文件

公开仓库不提供这些参数，也不分发完整真实曲库。缺少曲库时服务会以 degraded 状态启动，真实登录入口返回清晰错误；Mock 模式不受影响。认证细节见 [docs/AUTH.md](docs/AUTH.md)。

## 架构

```text
Web（已验证） ─┐
               ├─ FastAPI ─ 成绩标准化 ─ RKS Engine ─ Push Planner
小程序原型 ────┘              │
                         内存短期会话
```

Web 是当前经过实际验证的入口。`miniprogram/` 复用同一 API，但仍是未完成端到端验证的原型。完整说明与 API 列表见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 推分算法

PhiPush 会测试多个 ACC 增量、常用精度节点、B27 入选线和下一档两位小数显示线，并为每个候选重新计算完整的 P1–P3 + B1–B27。推荐分数大致衡量“预计总 RKS 收益 / 估算练习成本”，并对高 ACC 和 100% 目标增加惩罚。

它是 heuristic / estimate，不是全局最优解，也不保证推荐谱面在实际体感上最容易。公式、候选生成和目标路线见 [docs/ALGORITHM.md](docs/ALGORITHM.md)。

## 安全与数据

- 只访问当前用户本人明确授权后的数据
- SessionToken 仅在一次只读加载流程中短暂使用，不写入数据库、普通 JSON 或日志
- Web 使用 HttpOnly cookie 和随机短期会话；默认 15 分钟后失效，重启服务立即清空
- 不提交真实 Token、Cookie、账号标识、成绩或私人存档
- 不提供云存档上传、成绩修改或作弊功能
- Python 无法保证敏感字符串立即从进程内存物理擦除；公开部署仍需 HTTPS、日志控制、CORS 和限流

仓库只包含虚构的 `data/demo_charts.json` 与 `data/mock_player.json`。完整真实曲库不随仓库分发；使用者必须自行确认本地数据的使用权。更多认证与凭证处理说明见 [docs/AUTH.md](docs/AUTH.md)。

## 微信小程序状态

`miniprogram/` 是尚未发布的原型，不是当前正式支持的入口。它仍缺少：

- 正式微信小程序 AppID
- HTTPS 与微信网络域名配置
- 对 TapTap 登录全部中间状态的正确处理
- 微信开发者工具完整验收
- 真机端到端验证与发布审核

默认 `touristappid` 和 `127.0.0.1` 配置不能直接用于真机或公开环境。

## 测试

```bash
pytest
```

测试覆盖 RKS 公式与边界、P1–P3/B1–B27、cutoff、替换模拟、目标 ACC 反推、推荐排序、目标路线、未知谱面、空成绩和 Mock API 流程。

## 当前限制

- 真实登录只完成过作者本人账号的一次端到端验证，没有公开的真实存档测试夹具
- TapTap、LeanCloud 与 Phigros 云存档流程不是面向本项目承诺稳定的公共 API
- 公开仓库不分发完整真实曲库，真实模式不能在全新克隆后零配置运行
- 推荐算法没有个人练习历史、谱面体感或严格的全局最优求解
- 内存会话适合本地单进程使用，不是成熟公共服务架构
- 微信小程序尚未完成正式环境验证

## Future Work

- 获得适用于公开服务的 TapTap / Phigros 授权与应用配置
- 建立许可清晰、版本可追溯的曲库更新方式
- 用个人历史表现改善练习成本估算
- 增加可公开的固定二进制解析回归样本
- 完成小程序登录流程、开发者工具和真机验证
- 在满足安全与合规要求后部署 HTTPS 服务

## License / Third-party notice

原创代码使用 [MIT License](LICENSE)。第三方项目、数据来源与权利边界见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。MIT 许可证不授予任何 Phigros、Pigeon Games、TapTap、WeChat、曲名、谱面或游戏资源权利。
