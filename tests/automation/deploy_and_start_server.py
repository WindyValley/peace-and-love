#!/usr/bin/env python3
"""T-PRICE-001 真机编排：部署 jar → 启测试服 → 等就绪。

只负责把最新「带 verify RPC」的 neoforge jar 部署到 192.0.2.10 并等到
数据包加载完成（pricing.scan 依赖 reloadableRegistries）。比对由
verify_pricing_scan_golden.py 负责，两者可分开跑（服务器启动慢）。

用法：
  python tests/automation/deploy_and_start_server.py [jar路径]
"""
import subprocess
import sys
import time
from pathlib import Path

HOST = "mc@192.0.2.10"
REMOTE = "/home/mc/minecraft"
ROOT = Path(__file__).resolve().parents[2]
JAR = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    ROOT / "neoforge/build/libs/peaceandlove-0.0.2.jar"
READY_MARK = 'Done ('          # 服务器启动完成日志标志
RPC_PORT = 25585


def ssh(cmd, timeout=60):
    return subprocess.run(["ssh", "-o", "ConnectTimeout=8", HOST, cmd],
                          capture_output=True, text=True, timeout=timeout)


def main():
    if not JAR.exists():
        sys.exit(f"找不到 jar: {JAR}（先 ./gradlew :neoforge:build -PenableVerifyRpc=true）")

    # 0) 确认当前没在跑（检查 25565 监听，避免 pgrep 匹配到自身命令行）
    r = ssh("(ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | grep -q ':25565 ' && echo RUNNING || echo STOPPED")
    if r.stdout.strip() == "RUNNING":
        sys.exit("服务器 25565 已在监听，先停服再部署")

    # 1) 移除 mods 下旧 peaceandlove jar（备份到 mods_backup，不放第二个 jar）
    print(">> 备份并移除旧 mod jar ...")
    print(ssh(f"mkdir -p {REMOTE}/mods_backup && "
              f"mv -f {REMOTE}/mods/peaceandlove-*.jar {REMOTE}/mods_backup/ 2>/dev/null; "
              f"ls {REMOTE}/mods").stdout)

    # 2) 上传新 jar
    print(f">> 上传 {JAR.name} ...")
    subprocess.run(["scp", "-o", "ConnectTimeout=8", str(JAR),
                    f"{HOST}:{REMOTE}/mods/"], check=True, timeout=120)
    print(ssh(f"ls -la {REMOTE}/mods/peaceandlove-*.jar").stdout)

    # 3) 启动服务器（nohup，独立于 ssh 会话）
    print(">> 启动测试服 ...")
    ssh(f"cd {REMOTE} && setsid sh run.sh nogui > server_stdout.log 2>&1 < /dev/null &", timeout=20)

    # 4) 轮询日志等就绪（最多 180s）
    print(">> 等待数据包加载完成 ...")
    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(5)
        r = ssh(f"grep -c '{READY_MARK}' {REMOTE}/server_stdout.log 2>/dev/null || true")
        if r.stdout.strip() not in ("", "0"):
            print(">> 服务器就绪")
            # 再等 2s 确保服务稳定
            time.sleep(2)
            print(">> 现在可运行: python tests/automation/verify_pricing_scan_golden.py")
            return
        # 检查是否崩溃
        err = ssh(f"grep -E 'Failed to|FATAL|Crash report' {REMOTE}/server_stdout.log | tail -3")
        if err.stdout.strip():
            print("!! 日志疑似报错:\n", err.stdout)
    sys.exit("等待服务器启动超时（180s）")


if __name__ == "__main__":
    main()
