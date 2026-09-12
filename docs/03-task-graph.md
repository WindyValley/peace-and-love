# Peace And Love — 任务依赖图

- 版本：v1.0
- 日期：2026-09-11
- 配套：`03-decomposition.md`

---

## 1. 全局依赖图

```mermaid
graph TD
    classDef critical fill:#7f1d1d,stroke:#ef4444,color:#fff
    classDef normal fill:#1e3a5f,stroke:#3b82f6,color:#fff
    classDef parallel fill:#14532d,stroke:#22c55e,color:#fff
    classDef gated fill:#78350f,stroke:#f59e0b,color:#fff

    S1["T-SETUP-001<br/>探针→正式工程"]:::critical
    S2["T-SETUP-002<br/>Git 初始化"]:::normal
    S3["T-SETUP-003<br/>包结构骨架"]:::critical
    S4["T-SETUP-004<br/>CI"]:::normal

    C1["T-CFG-001<br/>PalConfig"]:::critical
    C2["T-CFG-002<br/>JSON 读写"]:::normal
    C3["T-CFG-003<br/>reload 命令"]:::normal
    C4["T-CFG-004<br/>whitelist 命令"]:::normal

    SC1["T-SCOPE-001<br/>AdaptedMobs 38"]:::critical
    SC2["T-SCOPE-002<br/>门控判定"]:::critical
    SC3["T-SCOPE-003<br/>未适配日志"]:::normal

    P1["T-PRICE-001<br/>LootTableScanner"]:::parallel
    P2["T-PRICE-002<br/>对数曲线"]:::parallel
    P3["T-PRICE-003<br/>PriceTable"]:::parallel
    P4["T-PRICE-004<br/>单调性自检"]:::parallel

    TR1["T-TRADE-001<br/>MobMerchantMixin"]:::critical
    TR2["T-TRADE-002<br/>TradeOfferBuilder"]:::normal
    TR3["T-TRADE-003<br/>右键开 GUI"]:::normal
    TR4["T-TRADE-004<br/>RestockManager"]:::normal
    TR5["T-TRADE-005<br/>NBT 持久化"]:::normal

    N1["T-NEUT-001<br/>Strategy 接口"]:::critical
    N2["T-NEUT-002<br/>GoalBased 32"]:::critical
    N3["T-NEUT-003<br/>BrainBased 6"]:::critical
    N4["T-NEUT-004<br/>restore 可逆"]:::normal
    N5["T-NEUT-005<br/>特殊 A 组"]:::critical
    N6["T-NEUT-006<br/>特殊 B 组"]:::normal
    N7["T-NEUT-007<br/>特殊 C 组"]:::normal

    A1["T-ANGER-001<br/>hurt 注入点"]:::critical
    A2["T-ANGER-002<br/>AngerController"]:::critical
    A3["T-ANGER-003<br/>KinAlerter"]:::critical
    A4["T-ANGER-004<br/>脱战冷却"]:::normal

    T1["T-TEST-001<br/>定价单测"]:::parallel
    T2["T-TEST-002<br/>门控单测"]:::parallel
    T3["T-TEST-003<br/>补货单测"]:::parallel
    T4["T-TEST-004<br/>P2 验证"]:::gated

    R1["T-REL-001<br/>真机验证"]:::critical
    R2["T-REL-002<br/>README"]:::normal
    R3["T-REL-003<br/>LICENSE"]:::normal
    R4["T-REL-004<br/>平台页面"]:::normal
    R5["T-REL-005<br/>🔒 发布"]:::gated

    S1 --> S2 --> S4
    S1 --> S3
    S3 --> C1 --> C2 --> C3 --> C4
    S3 --> SC1 --> SC2
    C1 --> SC2
    SC2 --> SC3

    S3 --> P1 --> P2 --> P3 --> P4

    SC2 --> TR1 --> TR3
    P3 --> TR2
    TR1 --> TR2 --> TR4 --> TR5

    SC2 --> N1 --> N2
    N1 --> N3
    N2 --> N4
    N3 --> N4
    N2 --> N5
    N2 --> N6
    N3 --> N6
    N2 --> N7

    N1 --> A1 --> A2 --> A3
    A2 --> A4

    P4 --> T1
    SC2 --> T2
    TR4 --> T3
    TR3 --> T4

    N5 --> R1
    N6 --> R1
    N7 --> R1
    A3 --> R1
    A4 --> R1
    TR5 --> R1
    T4 --> R1

    R1 --> R2 --> R4 --> R5
    R3 --> R5
```

**图例：**

- 🔴 红色 = 关键路径
- 🔵 蓝色 = 普通任务
- 🟢 绿色 = 可并行（不在关键路径）
- 🟠 橙色 = 需门控/人工确认

---

## 2. 关键路径（最长串行链）

```mermaid
graph LR
    classDef cp fill:#7f1d1d,stroke:#ef4444,color:#fff

    A["T-SETUP-001<br/>3h"]:::cp --> B["T-SETUP-003<br/>2h"]:::cp
    B --> C["T-CFG-001<br/>3h"]:::cp
    C --> D["T-SCOPE-002<br/>3h"]:::cp
    D --> E["T-NEUT-001<br/>3h"]:::cp
    E --> F["T-NEUT-002<br/>6h"]:::cp
    F --> G["T-NEUT-005<br/>8h"]:::cp
    G --> H["T-REL-001<br/>8h"]:::cp
    H --> I["T-REL-002<br/>4h"]:::cp
    I --> J["T-REL-004<br/>4h"]:::cp
    J --> K["T-REL-005<br/>2h"]:::cp
```

**关键路径累计：3+2+3+3+3+6+8+8+4+4+2 = 46h**

另有一条几乎等长的仇恨链：

```
T-NEUT-001(3h) → T-ANGER-001(4h) → T-ANGER-002(5h) → T-ANGER-003(5h) → T-REL-001
累计到 T-REL-001 前：17h
```

两条链在 `T-REL-001` 汇合，**实际关键路径取较长者 ≈ 62h**（含 Sprint 间切换开销）。

---

## 3. Sprint 泳道图

```mermaid
graph TB
    subgraph S1["Sprint 1 — 骨架与基础设施 (30h)"]
        direction LR
        s1a["SETUP 001~004"]
        s1b["CFG 001~004"]
        s1c["SCOPE 001~003"]
        s1a --> s1b --> s1c
    end

    subgraph S2["Sprint 2 — 核心功能 (52h)"]
        direction LR
        s2a["PRICE 001~004"]
        s2b["TRADE 001~005"]
        s2c["NEUT 001~004"]
        s2a --> s2b
    end

    subgraph S3["Sprint 3 — 特殊适配与仇恨 (48h)"]
        direction LR
        s3a["NEUT 005~007"]
        s3b["ANGER 001~004"]
        s3c["TEST 001~004"]
    end

    subgraph S4["Sprint 4 — 发布 (20h)"]
        direction LR
        s4a["REL 001~005"]
    end

    S1 --> S2 --> S3 --> S4
```

---

## 4. 里程碑验收点

| 里程碑 | 时点 | 验收标准 | 验证方式 |
|--------|------|---------|---------|
| **M1** | Sprint 1 末 | 服务端启动、`reload`/`whitelist` 命令可用、门控判定正确（尚无行为变化） | 服务端实测 + 单测 |
| **M2** | Sprint 2 末 | 38 生物不主动攻击、右键开交易界面、价格正确、每日 1 次 | **必须真机** |
| **M3** | Sprint 3 末 | 仇恨三条硬约束全满足、10 个特殊生物行为正确、P2 结论明确 | **必须真机** |
| **M4** | Sprint 4 末 | v1.0 发布 | **须用户确认** |

---

## 5. 阻塞关系提示

| 若卡住 | 会阻塞 | 建议 |
|--------|--------|------|
| T-SETUP-001 | **全部** | 最高优先，探针工程已验证可直接演进 |
| T-SCOPE-002 | TRADE / NEUT / TEST 三个 Epic | 门控是枢纽，务必先做对 |
| T-NEUT-002 | 全部特殊适配 | `removeAllGoals(Predicate)` 已验证存在 |
| T-TEST-004 (P2) | 发布文案定位 | 若不成立需改宣传口径，故提前到 Sprint 3 |

---

## 变更记录

| 日期 | 版本 | 作者 | 变更 |
|------|------|------|------|
| 2026-09-11 | v1.0 | Hermes | 初版依赖图 |
