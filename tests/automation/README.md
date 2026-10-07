# 真机自动化测试

本目录是 peace-and-love 的**真机行为验证脚本**：在一台专用服务器上部署本
mod，用真实 Minecraft 客户端连入，脚本驱动玩家走位/攻击/跳跃，再读取怪物
的愤怒、示警、攻击目标等状态做断言。单元测试覆盖不了「怪到底打不打玩家」，
这类验证必须在真客户端 + 真服务器上跑。

## 依赖

这些脚本本身只含标准库，但它们依赖一个**独立项目 mc-client-rpc** 作为驱动：

| 通道 | 端口 | 作用 |
|---|---|---|
| mc-client-rpc JSON-RPC | `25586` | 操控客户端玩家（走/打/跳/视角）|
| Minecraft RCON | `25575` | 在专用服务器上召唤/清场/查询 |
| peace-and-love 调试探针 | `25585` | 读取 mod 自己记录的愤怒来源等 |

驱动代码（`combat_loop_test.py`、`rcon.py`）不放在本仓库，保持单一来源，
位于 mc-client-rpc 项目的 `scripts/` 下。各脚本通过脚本内的
`sys.path.insert(0, .../mc-client-rpc/scripts)` 引用它。运行前需要本机已
克隆 mc-client-rpc，且：

1. 专用服务器已启动、已部署最新 peace-and-love jar；
2. 客户端（`runClient`）已启动，mods 下同时装 peace-and-love + mc-client-rpc；
3. 玩家 `Dev` 已连入测试服。

可用 mc-client-rpc 的 `scripts/launch_and_connect.py` 完成客户端启停与连接。

## 运行

```bash
python tests/automation/<脚本名>.py
```

部分脚本带参数（如 `verify_alert_anger_big.py <type>`），见各脚本顶部说明。

## 覆盖的行为

- 同族示警边界（玩家攻击后，附近同族是否被叫醒、多远以外不被叫醒）
- 脱战恢复（时间到 / 距离拉开后怪物是否回到中立）
- 怪物互殴与玩家示警的区分
- 白名单热切换
- 大碰撞箱怪物（守卫者/恶魂/幻翼等）的示警
