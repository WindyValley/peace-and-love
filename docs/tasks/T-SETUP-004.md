- [x] T-SETUP-004: GitHub Actions 双端构建 CI

**完成备注：** .github/workflows/build.yml（JDK21 temurin+Gradle 缓存+artifact）；gh run list 显示 build 多次 success（最近 v0.0.2）
**优先级：** P1
**预估：** 3h
**Owner：** agent
**依赖：** T-SETUP-002
**可并行：** T-CFG-001

## 目标

配置 CI，push 与 PR 时自动构建双端 jar 并跑单测。

## 来源

- 需求：`../01-requirements.md` §4 非功能需求

## 验收标准

- [x] `.github/workflows/build.yml` 存在
- [x] JDK 21 (temurin)，Gradle 缓存启用
- [x] `./gradlew build` 双端通过
- [x] 产物上传为 artifact
- [x] CI 在 GitHub 上实际跑绿一次

## 技术要点

- 注意 Gradle wrapper 校验（`gradle/wrapper/gradle-wrapper.jar` 需入库）
- 用 `actions/setup-java@v4` + `gradle/actions/setup-gradle@v4`

## 产出物

- 代码：`.github/workflows/build.yml`
- Commit：`ci: 添加双端构建工作流`

## 备注

无
