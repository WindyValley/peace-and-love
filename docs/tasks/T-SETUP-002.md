- [ ] T-SETUP-002: Git 仓库初始化

**优先级：** P0
**预估：** 1h
**Owner：** agent
**依赖：** T-SETUP-001
**可并行：** T-SETUP-003

## 目标

初始化 git 仓库，配置 .gitignore，完成首次提交。

## 来源

- 用户偏好：分批次提交，CHANGELOG 风格中文 commit message

## 验收标准

- [ ] `git init` 且默认分支为 `main`
- [ ] `.gitignore` 覆盖 `build/` `.gradle/` `run/` `*.log` `.idea/`
- [ ] `spikes/` 下的 jar 与 mappings 大文件被忽略（`server-*.jar` / `server_mappings.txt`）
- [ ] 首次提交成功，`git status` 干净

## 技术要点

- 大文件确认：`server-1.21.1.jar` 约 50 MB，`server_mappings.txt` 约 8 MB，**必须忽略**
- spike 的分析脚本与 JSON 结论要保留入库（体积小、是决策依据）

## 产出物

- 代码：`.gitignore`
- Commit：`chore: 初始化 git 仓库`

## 备注

无
