# T-REL-004: Modrinth / CurseForge 页面文案

**状态：** todo
**优先级：** P0
**预估：** 4h
**Owner：** 人工 + agent
**依赖：** T-REL-002
**可并行：** T-REL-003

## 目标

撰写发布平台页面文案，准备截图与标签。

## 来源

- 用户偏好：面向玩家的文案，不是开发日志

## 验收标准

- [ ] 简介一句话说清玩法
- [ ] 详细描述含玩法演示截图（至少 3 张）
- [ ] 截图展示：交易界面、中立的怪物群、配置命令
- [ ] 标签选择（Adventure / Utility / Game Mechanics）
- [ ] 版本兼容性标注（1.21.1 / Fabric / NeoForge）
- [ ] 依赖标注（Architectury API）
- [ ] 中英双语描述

## 技术要点

Modrinth 与 CurseForge 的 markdown 支持略有差异，
CurseForge 对 HTML 更宽容，Modrinth 更严格。建议先写 Modrinth 版本。

⚠️ **P2 结论影响文案**：若客户端需装模组，必须在页面显著位置标注，
否则玩家会遇到连不上服务器的困惑。

## 产出物

- 文档：`docs/modrinth-page.md`、`docs/curseforge-page.md`
- Commit：`docs: 添加发布平台页面文案`

## 备注

无
