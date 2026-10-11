- [ ] T-PRICE-002.2: 定价锚点接配置：epk_cheap/epk_rare/price_max 从配置读取

**优先级：** P0
**预估：** 2h
**Owner：** agent
**依赖：** T-PRICE-002.1，T-CFG 配置域（ConfigManager）；上游 T-PRICE-001
**可并行：** T-CFG-003

## 目标

把对数曲线的三个锚点接到配置：启动与 /reload 时从配置读取，供定价表构建使用。

## 来源

- 设计：../02-design.md §3.3 定价引擎、§5.1 启动时构建定价表
- 决策：../adr/003
- 拆分自：T-PRICE-002

## 验收标准

- [ ] epk_cheap / epk_rare / price_max 全部从配置读取，默认值与设计一致（2 / 0.005 / 128）
- [ ] 配置热重载（/reload）后，定价表用新锚点重建
- [ ] 调用方把配置锚点传入 PricingEngine.price，纯逻辑层不持有配置
- [ ] 非法/越界配置有兜底与 WARN，不崩服

## 技术要点

- 锚点校验已在 PricingEngine 内，绑定层负责装载默认值与合法性回退

## 产出物

- 代码：定价配置绑定（接 ConfigManager）
- 测试：配置锚点装载/回退单测
- Commit：待提交

## 备注

无
