# Third-party notices

PhiPush 的 MIT 许可证只适用于本仓库原创代码，不授予任何 Phigros、Pigeon Games、TapTap、WeChat、曲目名称、谱面或游戏资源权利。

## 参考实现

| Project | URL | License | How referenced |
|---|---|---|---|
| Phi-CloudAction-python | https://github.com/wms26/Phi-CloudAction-python | GPL-3.0 | 协议和算法研究；未复制源码 |
| PhigrosLibrary | https://github.com/7aGiven/PhigrosLibrary | GPL-3.0 | 云存档格式研究；未复制源码或数据 |
| phi-plugin | https://github.com/Catrong/phi-plugin | 见上游仓库 | TapTap/LeanCloud 流程研究；未复制源码或数据 |
| phigros-save-manager | https://github.com/lamadaemon/phigros-save-manager | 见上游仓库 | 二进制格式交叉核对；未复制源码或数据 |
| Phigros_Resource | https://github.com/7aGiven/Phigros_Resource | GitHub 当前显示 GPL-3.0 | 只作为本地数据生成方式的研究背景；公开仓库不分发其完整数据或资源 |

准备公开版本时再次检查发现，Phigros_Resource 当前显示 GPL-3.0，但其内容来自游戏 APK。为避免对资源再授权范围作不可靠判断，PhiPush 公开仓库不包含由它生成的完整 `data/charts.json`。

`data/demo_charts.json` 和 `data/mock_player.json` 是本项目为测试创建的虚构数据，不对应真实玩家或完整游戏曲库。

运行时 Python 依赖保留各自许可证。PhiPush 是非官方只读社区工具，与 Pigeon Games、Phigros、TapTap、WeChat 没有隶属、授权或背书关系；第三方接口不保证长期可用。
