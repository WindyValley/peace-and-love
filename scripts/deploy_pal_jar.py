#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署 peace-and-love mod 到测试服务器并重启。

流程（幂等,任何一步失败即停）：
  1. 本地构建: ./gradlew :neoforge:build
  2. scp 推 jar 到服务器 ~/minecraft/mods/
  3. RCON stop 优雅关闭服务器
  4. 等进程退出
  5. ssh setsid 重启服务器
  6. 轮询 RCON list 直到服务器上线

用法:
    python scripts/deploy_pal_jar.py
"""
import subprocess
import sys
import time
import os
from pathlib import Path

# 复用 mc-client-rpc 工具库的 Source RCON 客户端（位置可用环境变量覆盖）
_MCRPC_SCRIPTS = os.environ.get(
    "MCRPC_SCRIPTS", r"D:\Coding\projects\mc-client-rpc\scripts")
sys.path.insert(0, _MCRPC_SCRIPTS)
# 本脚本属私有部署，注入本机测试服默认（通用库不再内置这些值）。
# 必须在 `import rcon` 之前设置：库在导入时固化默认连接参数。
os.environ.setdefault("MCRPC_RCON_HOST", "192.0.2.10")
os.environ.setdefault("MCRPC_SSH_TARGET", "mc@192.0.2.10")
os.environ.setdefault("MCRPC_SERVER_DIR", "~/minecraft")
from rcon import get_password, open_default, RconError

# 项目根 = 本脚本（scripts/）的上一级，跟仓库走，不写死本机路径
PAL_DIR = Path(__file__).resolve().parent.parent


def read_mod_version() -> str:
    """从 gradle.properties 读 mod_version（版本号唯一来源），不写死。"""
    for line in (PAL_DIR / "gradle.properties").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("mod_version"):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("gradle.properties 中找不到 mod_version")


MOD_VERSION = read_mod_version()
JAR_NAME = f"peaceandlove-{MOD_VERSION}.jar"
LOCAL_JAR = PAL_DIR / "neoforge" / "build" / "libs" / JAR_NAME
SSH_TARGET = "mc@192.0.2.10"
REMOTE_JAR = f"/home/mc/minecraft/mods/{JAR_NAME}"
REMOTE_WORK = "/home/mc/minecraft"


def sh(cmd: list[str], timeout: int = 60, desc: str = "", cwd: Path | None = None) -> subprocess.CompletedProcess:
    """跑本地命令,实时回显,失败即抛。"""
    print(f"[sh] {' '.join(str(c) for c in cmd)}" + (f"  # {desc}" if desc else ""))
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       cwd=str(cwd) if cwd else None)
    if p.returncode != 0:
        print(f"STDOUT:\n{p.stdout}")
        print(f"STDERR:\n{p.stderr}")
        raise RuntimeError(f"命令失败 (exit {p.returncode}): {desc or cmd[0]}")
    return p


def ssh(remote_cmd: str, timeout: int = 30, desc: str = "") -> subprocess.CompletedProcess:
    """跑远程命令。"""
    return sh(["ssh", SSH_TARGET, remote_cmd], timeout=timeout, desc=desc or remote_cmd)


def wait_rcon_up(timeout: float = 120, interval: float = 3) -> None:
    """轮询 RCON 直到能连上并响应 list。"""
    pw = get_password()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open_default() as r:
                resp = r.command("list")
                print(f"[rcon] list => {resp}")
                return
        except (RconError, OSError) as e:
            print(f"[rcon] 未就绪 ({e.__class__.__name__}), {interval}s 后重试…")
            time.sleep(interval)
    raise RuntimeError(f"等服务器上线超时 ({timeout}s)")


def wait_process_exit(timeout: float = 60, interval: float = 2) -> None:
    """轮询远程 MC java 进程,直到消失。

    关键：用 pgrep -x java (精确进程名),不能 pgrep -f (会匹配到
    发起查询的 ssh 自己的 bash,因为命令行里也包含模式字符串)。
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        p = ssh("pgrep -x java; true", desc="查 MC java 进程")
        if not p.stdout.strip():
            print("[proc] MC java 进程已退出")
            return
        print(f"[proc] java 仍在运行 (pid={p.stdout.strip()}), {interval}s 后重试…")
        time.sleep(interval)
    raise RuntimeError(f"等 MC 进程退出超时 ({timeout}s)")


def main() -> int:
    print("=" * 60)
    print("部署 peace-and-love mod 到测试服务器")
    print("=" * 60)

    # 1. 构建（测试服需要验证端口，显式开启构建开关）
    print("\n[1/6] 构建 neoforge jar（-PenableVerifyRpc=true）…")
    # Windows 下 subprocess 不能直接跑 ./gradlew shell 脚本,用 cmd 调 gradlew.bat
    sh(["cmd", "/c", "gradlew.bat", ":neoforge:build", "-x", "test",
        "-PenableVerifyRpc=true"],
       timeout=600, desc="Gradle 构建", cwd=PAL_DIR)
    if not LOCAL_JAR.exists():
        raise RuntimeError(f"构建产物不存在: {LOCAL_JAR}")
    size = LOCAL_JAR.stat().st_size
    print(f"    构建产物: {LOCAL_JAR} ({size} bytes)")

    # 2. scp 推 jar
    print("\n[2/6] 推 jar 到服务器…")
    sh(["scp", str(LOCAL_JAR), f"{SSH_TARGET}:{REMOTE_JAR}"],
       timeout=120, desc="scp 上传")
    # 清掉 mods 里其他版本的旧 peaceandlove jar，避免两个版本同时被加载
    removed = ssh(
        f"cd {REMOTE_WORK}/mods && ls peaceandlove-*.jar 2>/dev/null "
        f"| grep -v -x '{JAR_NAME}' | tee /dev/stderr | xargs -r rm -f; true",
        desc="清理旧版本 jar")
    if removed.stderr.strip():
        print(f"    已删旧 jar: {removed.stderr.strip()}")
    else:
        print("    无旧版本 jar 残留")

    # 3. RCON stop
    print("\n[3/6] RCON stop 优雅关闭服务器…")
    try:
        pw = get_password()
        with open_default() as r:
            r.command("save-all")
            print("    save-all 完成")
            r.command("stop")
            print("    stop 指令已发")
    except (RconError, OSError) as e:
        # stop 命令发出后连接会断,这是预期的
        print(f"    RCON 连接关闭（预期）: {e.__class__.__name__}")

    # 4. 等进程退出
    print("\n[4/6] 等 MC 进程退出…")
    wait_process_exit(timeout=90)

    # 5. 重启服务器
    print("\n[5/6] ssh 重启服务器…")
    ssh(
        f"cd {REMOTE_WORK} && setsid nohup ./run.sh nogui > server.log 2>&1 < /dev/null &",
        desc="setsid 后台启动",
    )
    print("    启动命令已发")

    # 6. 等服务器上线
    print("\n[6/6] 等服务器上线…")
    wait_rcon_up(timeout=180, interval=5)

    print("\n" + "=" * 60)
    print("✓ 部署完成,服务器已上线")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n✗ 部署失败: {e}", file=sys.stderr)
        sys.exit(1)
