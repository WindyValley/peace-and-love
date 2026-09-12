# T-CFG-004: /pal whitelist 命令族

**状态：** todo
**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-CFG-003
**可并行：** 无

## 目标

实现白名单的增删查命令，变更后持久化并立即生效。

## 来源

- 设计：`../02-design.md` §7
- 需求：FR-3.2

## 验收标准

- [ ] `whitelist list` 列出当前白名单（含中文名）
- [ ] `whitelist add <id>` / `remove <id>` 支持 tab 补全
- [ ] 补全候选来自**已适配列表**，避免输入无效 id
- [ ] 变更后自动保存配置文件
- [ ] 对未适配 id（如末影龙）给出 INFO 提示但仍允许添加
- [ ] 变更立即影响已加载实体

## 技术要点

用 `SuggestionProvider` 提供补全；id 支持带/不带 `minecraft:` 前缀。

## 产出物

- 代码：`config/ConfigCommand.java`
- Commit：`feat(config): 实现白名单管理命令`

## 备注

无
