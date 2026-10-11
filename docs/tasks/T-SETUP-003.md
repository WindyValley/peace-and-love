- [ ] T-SETUP-003: 包结构与分层骨架

**优先级：** P0
**预估：** 2h
**Owner：** agent
**依赖：** T-SETUP-001
**可并行：** T-SETUP-002

## 目标

按设计创建 7 个模块的包结构与空类骨架，建立分层依赖规则。

## 来源

- 设计：`../02-design.md` §1 工程结构、§2 分层与依赖规则

## 验收标准

- [ ] 创建 `config/` `scope/` `pricing/` `trade/` `neutralize/` `anger/` `mixin/` 七个包
- [ ] 每个包有 `package-info.java` 说明职责与依赖方向
- [ ] `PeaceAndLove.java` 入口类可被两端初始化器调用
- [ ] 编译通过

## 技术要点

分层依赖规则（不得反向依赖）：
```
mixin → (trade, neutralize, anger) → scope → config
pricing → (独立，仅依赖 config)
```
`scope` 不得依赖 `trade`/`neutralize`，否则形成环。

## 产出物

- 代码：`common/src/main/java/top/windyvalley/peaceandlove/**`
- Commit：`feat: 建立分层包结构骨架`

## 备注

无
