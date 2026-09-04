# PhiPush

PhiPush 是一个本地优先、只读的 Phigros RKS 推分规划工具。

> **非官方声明：** PhiPush 是非官方第三方社区项目，与 Pigeon Games、Phigros、TapTap、WeChat（微信）没有隶属、合作、授权或背书关系。真实接口兼容性只代表有限的本地测试结果，不代表公开服务许可；第三方协议和接口可能随时变化或停止工作，本项目不保证其长期可用。它回答的不是“我打了多少分”，而是：**What should I grind next?**

项目同时提供 Web 网页和微信原生小程序两个入口。两端调用同一个 FastAPI API，共用同一份成绩解析、RKS 引擎、推分算法和 Mock 数据。

## 功能

- 短期 PhiPush 会话；Web 使用 HttpOnly cookie，小程序只持有短期会话 ID
- 当前 RKS、B30 cutoff、Phi/Best records、全部谱面成绩
- Top 10 推分机会：目标 ACC、单谱 RKS、总 RKS 增益、推荐理由
- 目标 RKS 的贪心近似路线
- 搜索歌曲、难度过滤，按 ACC、定数或单谱 RKS 排序
- 未知曲目安全降级，不因缺少定数而崩溃
- Mock 模式 42 条成绩，Web 与小程序取自同一个 `data/mock_player.json`
- SessionToken fallback；只在一次后端请求内使用，不落盘、不写日志

## 双端架构

```text
Web / 微信小程序
       │  PhiPush short-lived session
       ▼
FastAPI unified JSON API
       │
       ├─ TapTap / SessionToken → Phigros cloud (read only)
       └─ normalized PlayerRecord
                    │
          RKS Engine → Push Planner
```

API：`GET /api/health`、`POST /api/auth/taptap/start`、`GET /api/auth/taptap/status/{login_id}`、`POST /api/auth/session-token`、`POST /api/auth/mock`、`GET /api/player/{summary,records,best}`、`POST /api/analysis/{opportunities,target-route}`。交互式文档在 `/api/docs`。

## 安装

需要 Python 3.11+：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Mock 模式（推荐先运行）

```bash
python run.py --mock
```

打开 `http://127.0.0.1:8000`，点击“进入 Mock 演示”。不需要 TapTap、真实账号或微信 AppID。

### Real 模式

```bash
python run.py
```

打开 `http://127.0.0.1:8000`。若未配置可用的 TapTap OAuth client，页面会明确提示扫码登录暂不可用，并保留 SessionToken fallback。真实云存档协议不是官方稳定 API；游戏或服务升级后可能需要同步更新 LeanCloud 标识、加密参数或解析器。

`PHIGROS_CLIENT_ID`、`PHIGROS_CLIENT_TOKEN`、`LEANCLOUD_APP_ID`、`LEANCLOUD_APP_KEY`、`PHIGROS_AES_KEY_B64`、`PHIGROS_AES_IV_B64` 必须由使用者在本地通过环境变量或项目根目录的 `.env` 设置，参考 `.env.example`。公开仓库不提供或获取这些参数。不要把 SessionToken 或任何私有密钥提交进仓库。

## TapTap 与云存档流程

扫码模式使用 OAuth device-code：后端创建登录请求，客户端显示带倒计时的二维码/链接并轮询；授权完成后由后端换取 TapTap 身份和 LeanCloud SessionToken，然后只读下载最新 `_GameSave`、解密 ZIP 中的 `gameRecord`、标准化成绩，最后丢弃真实凭证并签发短期 PhiPush 会话。连接云存档时对安全的只读请求提供有限瞬时重试。

真实 TapTap → LeanCloud → Phigros 云存档 → gameRecord 链路已经由项目作者使用本人账号完成端到端验证。验证范围包括：TapTap 授权登录、本人玩家信息读取、云存档下载与解析、RKS 与游戏内结果核对、B30/Phi 与单曲成绩核对，以及基于真实成绩生成推分推荐。公开仓库不包含验证账号的昵称、标识、Token、Cookie、真实成绩或私人存档。

PhiPush 只访问当前用户本人明确授权后的数据，SessionToken fallback 使用同一个只读云存档客户端；项目没有任何上传或修改云存档的接口。该链路依赖非官方稳定协议，Phigros、Pigeon Games 或 TapTap 更新服务后可能需要调整，也可能停止工作。

## RKS 规则

单谱定数为 `C`、ACC 为百分数 `A`：

```text
A < 70:  rks = 0
A ≥ 70:  rks = C × ((A - 55) / 45)²
```

当前 RKS 使用固定的 3 个 Phi 奖励槽（P1–P3）和 27 个 Best 槽（B1–B27），总和除以 30。Best 从全部有效成绩中选取，因此同一张 Phi 谱面可以同时出现在 P 槽和 B 槽，并对总 RKS 贡献两次；不足 3 张 Phi 时空缺的 P 槽按 0 计算，不由额外 Best 补位。B30 cutoff 是 B27 的单谱 RKS。

公式与 B30 结构经以下公开实现交叉核对：[Phi-CloudAction-python](https://github.com/wms26/Phi-CloudAction-python)、[RankHub 的实现说明](https://github.com/qianmo2233/RankHub)、[phigros-b30-plugin](https://github.com/DeepSeek-V4-Pro/phigros-b30-plugin)。这些均非游戏官方规范，后续版本可能变化。公式、边界、排序、cutoff、替换和反推均有 pytest 覆盖。

## 推分算法

每张已知定数且未达 100% 的谱面会模拟 `+0.1 / +0.25 / +0.5 / +1 / +1.5 / +2% ACC`、常用精度节点（98 / 98.5 / 99 / 99.5 / 99.7 / 99.85 / 100）、刚好越过 B27 cutoff 的 ACC，以及让游戏内两位小数显示跨到下一档所需的最低 ACC。最后一项沿用了 [phi-plugin](https://github.com/Catrong/phi-plugin) 与 [phigros-b30-plugin](https://github.com/DeepSeek-V4-Pro/phigros-b30-plugin) 的实用目标思想，但 PhiPush 不直接套用“单谱增加量 × 30”：它会对每个候选重建完整 P1–P3 + B1–B27，得到真实的集合替换结果。

100% 候选会单独模拟 P1–P3。若它进入或抬高 P3，结果会把 `phi_gain` 与 `best_gain` 分开显示；同一张谱面同时属于 P 槽和 B 槽时，两份贡献都会计入。这样既不会漏掉 AP 的双槽收益，也不会把未进入 P3 的 100% 误算成额外收益。

```text
effort = ACC 提升量 × 凸形高精度惩罚 + 100% 额外惩罚
score = predicted total RKS gain / effort
```

高精度惩罚在 97%、99% 和 99.8% 后逐段加陡，避免把 `99.90 → 100.00` 与普通的 `97.00 → 97.10` 当成同等成本。跨过下一档两位小数显示线的候选获得很小的可解释加权。该 effort 只是保守的练习成本代理，并非谱面体感或玩家能力模型；在没有个人历史数据时，不声称能够判断哪张谱“实际更简单”。

目标路线在每一步重新计算全部机会，选择单位 ACC 收益最高者并迭代，最多 10 步。它是数学近似，不代表谱面体感难度，也不保证玩家实际结果。

## 微信小程序

1. 复制 `miniprogram/config.example.js` 为 `miniprogram/config.js`。
2. 修改 `API_BASE_URL`。
3. 在微信开发者工具中导入 `miniprogram/`；没有 AppID 时可使用测试号/游客模式完成大部分 Mock 调试。
4. 后端运行 `python run.py --mock`，小程序首页点击 “Demo / Mock 演示”。

开发者工具本机模拟器可尝试 `http://127.0.0.1:8000` 并关闭“校验合法域名”。**真机里的 localhost 指手机本身**，不能访问电脑；请改为电脑的局域网 IP，并让后端监听 `--host 0.0.0.0`，或使用部署后的 HTTPS API。

正式发布时，微信要求在小程序后台配置 HTTPS `request` 合法域名，不能使用 IP、端口或自签名证书。TapTap 第三方 OAuth 在同一手机上无法方便扫码，因此登录页同时提供二维码和“复制登录链接”；最终行为受微信 `web-view`、业务域名和 TapTap 当前授权策略限制。

小程序源码不包含 SessionToken 输入、不调用 `wx.setStorageSync` 保存凭证、不把真实凭证放进 URL 或日志。`config.js` 已被 `.gitignore` 忽略。

## 安全

**SessionToken 等同敏感账号凭证。不要泄露，不要截图分享，不要提交到 GitHub、Issue、日志或聊天记录。**

- 后端不记录请求正文，不把 token 写入 JSON/数据库/缓存文件
- token 仅在一次只读加载调用中短暂存在，`finally` 后清除局部引用
- 返回给客户端的只有随机的短期 PhiPush session
- 内存会话默认 15 分钟到期，服务重启立即失效
- 不包含上传、改分、作弊或云存档修改功能

生产部署仍需在反向代理层禁用请求体日志、启用 HTTPS、收紧 CORS，并用进程级密钥管理服务保存 OAuth 配置。

## 数据

公开仓库不分发完整 `data/charts.json`。仓库只包含完全虚构的 `data/demo_charts.json` 和对应 Mock 玩家，用于界面演示和测试。

真实模式需要使用者在本地准备自己有权使用的 `info.tsv` 与 `difficulty.tsv`，然后运行：

```bash
python scripts/update_chart_data.py /path/to/local/info-directory
```

生成的 `data/charts.json` 默认被 Git 忽略，也可以通过 `PHIPUSH_CHART_DATA` 指向其他本地路径。缺少完整曲库时服务仍可启动，`/api/health` 会返回 `degraded` 和清晰原因，真实登录接口返回 503；Mock 模式不受影响。未知谱面会显示 `Unknown chart` 并跳过无法计算的部分。使用者必须自行确认输入数据的访问、使用和再分发权利。

## 测试

```bash
pytest
```

覆盖单谱公式、70/100 边界、B30/Phi 排序、cutoff、Best 替换、目标 ACC 反推、push score、目标路线、未知谱面、空成绩、数据校验与 Mock API 端到端流程。

## 项目结构

```text
app/              FastAPI、统一 API、模板与核心服务
data/             Mock 玩家和打包谱面数据
miniprogram/      微信原生小程序
tests/            pytest 测试
run.py            Mock / Real 启动入口
```

## 截图

尚未纳入仓库。运行 Mock 模式后可从 Web Dashboard 和微信开发者工具预览并补充到 `docs/screenshots/`。

## 当前限制

- TapTap/Phigros 云端接口不是公开稳定的第三方查分 API，可能随服务更新失效，也不代表获得公开运营授权。
- 真实登录已完成一次端到端验证，但没有可提交到公开仓库的真实存档测试夹具；二进制解析仍主要依赖 Mock 与结构单元测试。
- 公开仓库不打包真实曲库；完整数据由使用者在本地自行准备。曲目名称、游戏资源及相关权利属于各自权利人。
- 算法不含谱面体感、玩家个人短板或练习时间模型。
- 内存会话适合单机 v0.1，不适合多实例部署。
- 小程序需要用户在微信开发者工具和真机上完成最终验证。

## Future Work

- 获得适用于公开服务的 TapTap / Phigros 授权与应用配置
- 合规构建可持续更新、版本可追溯的曲库数据
- 加入谱面标签与个人历史表现作为难度先验
- 为真实 gameRecord 版本增加固定二进制样本回归测试
- 部署 HTTPS API，并配置微信合法域名

## 开源与第三方

没有直接复制或 vendoring 上游代码。参考项目、许可证与用途见 `THIRD_PARTY_NOTICES.md`。若将来引入任何上游源码或完整数据，必须先确认许可证、保留版权声明并更新 notice。本项目与 Phigros、Pigeon Games、TapTap、WeChat（微信）没有官方隶属、合作、授权或背书关系。
