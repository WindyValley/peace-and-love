- [x] T-SETUP-001: 由探针工程演进为正式工程

**完成备注：** commit 2065317 由探针演进为正式工程骨架；双端 jar 已产出。验收2已勘误为 SemVer 0.x（现 0.0.2），探针保留在 spikes/ 归档
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** 无
**可并行：** 无

## 目标

把 `spikes/p1-p3-probe/` 提升为项目根工程，清理探针专用代码，保留全部已验证的 Gradle 配置。

## 来源

- 设计：`../02-design.md` §1 工程结构
- 验证：`../P1-P4-VERIFY.md`（探针工程构建已通过）

## 验收标准

- [x] 根目录出现 `build.gradle` / `settings.gradle` / `gradle.properties` / `gradlew`
- [x] `mod_version` 移除 `-probe` 后缀，版本号遵循 SemVer 0.x（正式发布前不用 1.0.0；现为 0.0.2，单一来源 gradle.properties，-PmodVersion 可覆盖）
- [x] 删除 `ProbeCommon.java` / `ProbeResults.java` / `*ProbeMixin.java` / `read_probe.py`
- [x] `./gradlew build` 双端通过
- [x] 产出 `fabric/build/libs/*.jar` 与 `neoforge/build/libs/*.jar`

## 技术要点

**必须原样保留以下已验证配置（改动会导致构建失败）：**
- Gradle **8.10.2** wrapper —— Gradle 9.x 与 Loom 1.7 不兼容
- `fabric/gradle.properties` 写 `loom.platform=fabric`
- `neoforge/gradle.properties` 写 `loom.platform=neoforge`
- `common/src/main/resources/peaceandlove.accesswidener` 保留（空文件即可，P1 已证明无需 AT）
- `architectury_api_version=13.0.11` / `neoforge_version=21.1.250` / `fabric_loader_version=0.16.9`

**Mixin 包纪律**：工具类不得放在 `top.windyvalley.peaceandlove.mixin` 包内，
否则抛 `IllegalClassLoadError: ... cannot be referenced directly`。

## 产出物

- 代码：项目根全部 Gradle 文件 + `common/fabric/neoforge` 三模块
- 测试：无
- Commit：`chore: 由 spike 探针工程演进为正式工程骨架`

## 备注

探针工程留在 `spikes/p1-p3-probe/` 不动，作为验证证据归档。
