- [x] T-CFG-003.1: /pal reload 命令本体与白名单即时切换

**完成备注：** 命令本体+白名单即时切换已完成（e09dad3/f2a1470），verify_whitelist_rollback 真机双向验证；定价表重建在 .2
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-CFG-002（ConfigManager.reload）
**可并行：** T-PRICE-002

## 目标

实现 /pal reload：OP 校验、委托 ConfigManager 原子重载、白名单变更即时作用于已加载实体、回显摘要、失败保留旧配置。

## 来源

- 拆分自：T-CFG-003

## 验收标准

- [x] /pal reload 需 OP 权限（level 2），/peaceandlove reload 别名同时注册
- [x] 重载后白名单变更立即影响已加载实体（触发 neutralize/restore 重判）
- [x] 返回反馈消息含变更摘要（ConfigManager.ReloadResult.message）
- [x] 重载失败时保留旧配置，整体替换实例，不进入半初始化状态
- [x] 白名单加→reload 恢复敌对、移除→再中立经真机双向验证（verify_whitelist_rollback）

## 技术要点

- 命令层只做参数解析与回显，业务全部委托已单测覆盖的 ConfigManager
- 命令注册/权限属运行时行为，纯 JUnit 无法覆盖，已随白名单回滚真机验证

## 产出物

- 代码：config/ConfigCommand.java#reloadNode
- 测试：ConfigManagerTest + tests/automation/verify_whitelist_rollback.py
- Commit：e09dad3、f2a1470

## 备注

命令本体与白名单链路已完成并真机验证；定价表重建见 .2
