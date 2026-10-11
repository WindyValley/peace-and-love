- [ ] T-SCOPE-003: 未适配生物的 INFO 日志提示

**优先级：** P2
**预估：** 1h
**Owner：** agent
**依赖：** T-SCOPE-002
**可并行：** 无

## 目标

管理员把未适配生物（如末影龙）加入白名单时，打 INFO 日志说明该配置无效。

## 来源

- 设计：`../02-design.md` §10 凋灵的处理

## 验收标准

- [ ] 加载配置时检测白名单中的未适配 id
- [ ] 打 INFO（非 WARN，这不是错误）
- [ ] 日志文案说明「该生物 v1.0 未适配，配置不生效，行为与原版一致」
- [ ] 每次 reload 只打一次，不刷屏

## 技术要点

用 `Set<String>` 去重已提示过的 id，reload 时清空。

## 产出物

- 代码：`scope/NeutralizationScope.java`
- Commit：`feat(scope): 未适配生物配置给出 INFO 提示`

## 备注

无
