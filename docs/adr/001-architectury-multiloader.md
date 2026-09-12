# ADR-001: 采用 Architectury 实现 Fabric + NeoForge 双加载器

## 状态

Accepted（2026-09-11）

## 背景

需求要求同时支持 Fabric 与 NeoForge 两个加载器（`../01-requirements.md` §4.1），首发版本为 Minecraft 1.21.1，且未来要扩展到 1.21.8 / 1.21.11。

约束条件：
- 单人开发，维护带宽有限
- 核心逻辑（定价、中立化、交易）与加载器无关，属于纯游戏逻辑
- 需要大量 Mixin（注入 `Merchant` 接口、`hurt` 触发点、战利品表 Accessor）
- 玩家群体分布在两个加载器上，只做一个会损失约半数用户

## 决策

采用 **Architectury** 作为多加载器抽象层，工程结构为 `common` / `fabric` / `neoforge` 三模块。

已核实的版本组合（2026-09-11）：

| 组件 | 版本 |
|------|------|
| Architectury Loom | `1.11.454` |
| Architectury API | `13.0.11` |
| Fabric API | `0.116.17+1.21.1` |
| NeoForge | `21.1.250` |
| Java | 21 |

Mixin 全部放在 `common` 模块，两端共用。平台差异（配置系统、事件注册）通过 `@ExpectPlatform` 处理。

## 后果

### 正面

- 核心逻辑写一遍，估计代码复用率约 85%
- Mixin 在 `common` 内双端通用 —— 这是最大收益，因为本项目 Mixin 占比高
- 版本迭代（1.21.8 / 1.21.11）时只需在单点修改
- Architectury 是社区主流方案，遇到问题有先例可查

### 负面

- 玩家需要额外安装 Architectury API 运行时依赖，增加一步安装门槛
- 构建产物三份，CI 时间约翻倍
- 平台专属 API 需走 `@ExpectPlatform` 或 service loader，多一层间接，调试时栈更深
- 绑死 Architectury 的版本节奏：若它对新 MC 版本支持滞后，本项目也会被拖住

### 中性

- 项目结构比单加载器复杂，但对熟悉 Architectury 的贡献者反而更清晰
- `common` 模块不单独发布，只作为构建中间产物

## 备选方案

### 选项 B：两套独立源码

- 优点：无第三方运行时依赖；各端可深度定制；不受 Architectury 版本节奏牵制
- 缺点：代码复用率 0；每个 bug 要修两遍；Mixin 要写两份；版本迭代成本 ×2
- 不选的原因：单人维护，双份维护成本不可承受。且本项目逻辑高度平台无关，双份代码几乎完全重复

### 选项 C：仅做 Fabric

- 优点：最简单，无抽象层开销，迭代最快
- 缺点：放弃约半数潜在用户；NeoForge 用户群体中整合包占比高
- 不选的原因：用户明确要求「两套都做」

## 回退路径

若 Architectury 对某个 MC 版本支持滞后超过可接受时间，退到选项 B。届时 `common` 模块的逻辑已与平台解耦，可直接复制为两份独立源码，迁移成本可控（主要工作是重写 `@ExpectPlatform` 的部分）。

## 参考资料

- Architectury 文档：https://docs.architectury.dev/
- 版本核实记录：`../SPIKE-REPORT.md` 环境侦查章节
