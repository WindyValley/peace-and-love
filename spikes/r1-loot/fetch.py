"""R1 spike step 1: 下载 1.21.1 client.jar 与 server.jar，提取原版战利品表 JSON。

战利品表在 1.21.1 中位于 client.jar 内 data/minecraft/loot_table/entities/*.json
（注意 1.21 起路径由 loot_tables 改为 loot_table 单数）。
"""
import json
import os
import sys
import urllib.request
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET_MC = "1.21.1"


def log(*a):
    print(*a, flush=True)


def main():
    vm = json.load(open(os.path.join(BASE, "vm.json"), encoding="utf-8"))
    url = next(v["url"] for v in vm["versions"] if v["id"] == TARGET_MC)
    log("[1] version json:", url)

    meta_path = os.path.join(BASE, "1.21.1.json")
    if not os.path.exists(meta_path):
        urllib.request.urlretrieve(url, meta_path)
    meta = json.load(open(meta_path, encoding="utf-8"))

    dl = meta["downloads"]
    log("[2] downloads available:", list(dl.keys()))
    for k, v in dl.items():
        log("    %-18s %10d bytes  %s" % (k, v["size"], v["url"]))

    # client.jar 含全部 data pack 资源（战利品表）
    jar_path = os.path.join(BASE, "client-1.21.1.jar")
    if not os.path.exists(jar_path):
        log("[3] downloading client.jar ...")
        urllib.request.urlretrieve(dl["client"]["url"], jar_path)
    log("[3] client.jar:", os.path.getsize(jar_path), "bytes")

    # 提取战利品表
    out_dir = os.path.join(BASE, "loot_tables")
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    prefixes_seen = set()
    with zipfile.ZipFile(jar_path) as z:
        names = z.namelist()
        for n in names:
            if "loot_table" in n and n.endswith(".json"):
                parts = n.split("/")
                # 记录前缀结构以确认路径约定
                prefixes_seen.add("/".join(parts[:4]))
                if "/entities/" in n:
                    rel = n.split("/entities/", 1)[1]
                    dst = os.path.join(out_dir, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with open(dst, "wb") as f:
                        f.write(z.read(n))
                    count += 1
    log("[4] loot_table path prefixes found:")
    for p in sorted(prefixes_seen):
        log("    ", p)
    log("[5] extracted entity loot tables:", count, "->", out_dir)

    if count == 0:
        log("!! 未找到实体战利品表，路径约定可能有变，打印部分候选：")
        with zipfile.ZipFile(jar_path) as z:
            cand = [n for n in z.namelist() if "loot" in n][:40]
        for c in cand:
            log("    ", c)
        sys.exit(1)


if __name__ == "__main__":
    main()
