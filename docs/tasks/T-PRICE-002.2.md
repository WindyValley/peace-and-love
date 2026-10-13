- [x] T-PRICE-002.2: 定价锚点接配置：epk_cheap/epk_rare/price_max 从配置读取

**完成备注：** ConfigurablePriceCurve 绑定层 + ConfigLoader 锚点关系校验（84467ec）；14 单测，common 全量 142 绿；纯JVM逻辑，游戏内价格待 003 PriceTable 接线后真机验证
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

- [x] epk_cheap / epk_rare / price_max 全部从配置读取，默认值与设计一致（2 / 0.005 / 128）
- [x] 曲线不缓存锚点，每次从当前 PalConfig 读取；ConfigManager.reload 后下一次定价立即用新锚点（端到端测验证）。定价表本身的 reload 重建由 T-PRICE-003 注册监听器接线
- [x] 调用方把配置锚点传入 PricingEngine.price，纯逻辑层不持有配置
- [x] 非法/越界配置有兜底与 WARN，不崩服

## 技术要点

- 纯函数 PricingEngine 负责数值关系（cheap>rare>0、max≥1）；ConfigurablePriceCurve 从当前 PalConfig 即时取参委托，无状态不缓存
- ConfigLoader 对 cheap>rare 的锚点关系做交叉校验，非法时回退默认锚点 + WARN + 回写（单字段范围 clamp 之外补的关系校验）

## 产出物

- 代码：common/.../pricing/ConfigurablePriceCurve.java（新增绑定层）；config/ConfigLoader.java（锚点关系交叉校验）
- 测试：ConfigurablePriceCurveTest（10）、ConfigLoaderTest（+2）、ConfigManagerTest（+2 真实 reload 端到端）
- Commit：84467ec

## 备注

无
