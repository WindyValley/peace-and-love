#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-TRADE-003 真机部署：把当前源码构建的 verify jar 部署到测试服并重启。

流程（全部在一个脚本内闭环，只需读最终结果）：
  1. RCON save-all + stop 优雅停服（若在跑），轮询 25565 关闭
  2. 备份远端旧 jar 到 mods_backup，scp 覆盖上传
  3. 本地/远端 jar 整文件 sha256 核对（同一文件上传，sha 必须一致）
  4. setsid 启服，轮询 25565 + verify-RPC(25585) 就绪

环境特定值（IP/路径/密码）按必传/常量集中在顶部，不写进通用工具。
用法：python tests/automation/deploy_server.py [jar路径]
"""
import hashlib
import subprocess
import sys
import time
from pathlib import Path

HOST = "mc@192.0.2.10"
IP = "192.0.2.10"
REMOTE = "/home/mc/minecraft"
RCON_PORT = 25575
RCON_PWD = "change-me"
GAME_PORT = 25565
RPC_PORT = 25585

ROOT = Path(__file__).resolve().parents[2]
JAR = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    ROOT / "neoforge/build/libs/peaceandlove-0.0.2.jar"
sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from rcon import Rcon  # noqa: E402


def ssh(cmd, timeout=60):
    return subprocess.run(["ssh", "-o", "ConnectTimeout=8", HOST, cmd],
                          capture_output=True, text=True, timeout=timeout)


def port_listening(port):
    r = ssh(f"(ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | grep -q ':{port} '")
    return r.returncode == 0


def wait_port(port, up, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_listening(port) == up:
            return True
        time.sleep(3)
    return False


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not JAR.exists():
        sys.exit(f"找不到 jar: {JAR}（先 ./gradlew :neoforge:build -PenableVerifyRpc=true -x test）")

    # 1) 在跑则优雅停服
    if port_listening(GAME_PORT):
        print(">> 服务器在跑，RCON save-all + stop ...")
        with Rcon(IP, RCON_PORT, RCON_PWD) as r:
            print("   save-all:", r.command("save-all").strip())
            print("   stop:", r.command("stop").strip())
        if not wait_port(GAME_PORT, False, timeout=120):
            sys.exit("!! 停服后 25565 仍在监听，放弃部署")
        time.sleep(3)
    else:
        print(">> 服务器未运行")

    # 2) 备份旧 jar + 上传
    print(">> 备份旧 jar 并上传新 jar ...")
    print(ssh(f"mkdir -p {REMOTE}/mods_backup && "
              f"mv -f {REMOTE}/mods/peaceandlove-*.jar {REMOTE}/mods_backup/ 2>/dev/null; true").stdout)
    subprocess.run(["scp", "-o", "ConnectTimeout=8", str(JAR),
                    f"{HOST}:{REMOTE}/mods/"], check=True, timeout=120)

    # 3) sha256 核对（同一文件上传，必须逐字节一致）
    local_sha = sha256(JAR)
    remote_sha = ssh(f"sha256sum {REMOTE}/mods/{JAR.name}").stdout.split()[0]
    print(f"   local : {local_sha}")
    print(f"   remote: {remote_sha}")
    if local_sha != remote_sha:
        sys.exit("!! sha256 不一致，上传可能损坏")
    print(">> jar 一致")

    # 4) 启服（setsid 已 detach；但 ssh channel 可能被 Java 继承的 fd 占住不返回，
    #    内存实测坑：裸 & 的 ssh 会超时报错而服务其实已起，故这里吞掉超时，
    #    下面以端口监听为唯一判据）
    print(">> 启动测试服 ...")
    try:
        ssh(f"cd {REMOTE} && setsid sh -c 'sh run.sh nogui > server_stdout.log 2>&1 < /dev/null' &",
            timeout=15)
    except subprocess.TimeoutExpired:
        print("   （ssh channel 15s 未返回，正常；以端口判活）")

    # 5) 等 25565 + 25585 都起来
    if not wait_port(GAME_PORT, True, timeout=240):
        sys.exit("!! 等待 25565 监听超时")
    print(">> 25565 已监听，再等 verify-RPC 25585 ...")
    if not wait_port(RPC_PORT, True, timeout=120):
        sys.exit("!! 25565 已起但 verify-RPC 25585 未起（jar 是否带 -PenableVerifyRpc=true？）")
    time.sleep(3)
    # 探活
    r = ssh(f"grep -c 'Done (' {REMOTE}/server_stdout.log 2>/dev/null || true").stdout.strip()
    print(f">> 部署完成，Done 标记计数={r}。可跑真机交互验证。")


if __name__ == "__main__":
    main()
