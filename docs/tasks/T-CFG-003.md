# T-CFG-003: /peaceandlove reload 热重载命令

**状态：** todo
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-CFG-002
**可并行：** T-PRICE-002

## 目标

实现配置热重载命令，重载后门控与定价立即生效，无需重启。

## 来源

- 设计：`../02-design.md` §7 命令设计
- 需求：FR-3.2

## 验收标准

- [ ] `/peaceandlove reload` 需 OP 权限（level 2）
- [ ] 重载后白名单变更立即影响已加载实体（调用 neutralize/restore）
- [ ] 重载后定价表重建
- [ ] 返回反馈消息含变更摘要
- [ ] 重载失败时保留旧配置，不进入半初始化状态

## 技术要点

**关键**：重载时白名单移入的生物要 `restore()`，移出的要 `neutralize()`，
需遍历已加载实体。依赖 T-NEUT-004 的可逆能力，若尚未完成可先只改判定、实体下次 tick 生效。

## 产出物

- 代码：`config/ConfigCommand.java`
- Commit：`feat(config): 实现 reload 热重载命令`

## 备注

无
