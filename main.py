"""入口：读 targets.yaml，先全量校验授权范围，通过后采集、检测、出报告。"""
import json
import os
import sys
from datetime import datetime

import yaml

from collectors.fingerprint import collect, pick_url
from collectors.ports import scan
from config import in_scope, load_scope
from detectors import DETECTORS
from detectors.normalize import normalize
from report.render import render_report


def write_records(records, outdir="reports"):
    os.makedirs(outdir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(outdir, "scan_" + stamp + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    return path


def arg_value(flag, default):
    if flag in sys.argv:
        index = sys.argv.index(flag) + 1
        if index < len(sys.argv):
            return sys.argv[index]
    return default


def run() -> int:
    path = arg_value("--targets", "targets.yaml")
    outdir = arg_value("--out", "reports")

    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    nets = load_scope(path)
    targets = cfg.get("targets") or []

    for ip in targets:
        if not in_scope(ip, nets):
            print("[拒绝] " + str(ip) + " 不在授权范围 " + str(nets) + ", 整体退出", file=sys.stderr)
            return 1
    print("[范围] " + str(len(targets)) + " 个目标全部在授权内")

    records = []
    for ip in targets:
        result = scan(ip)
        print("")
        print("== " + str(ip) + " ==")
        if not result.get("ok"):
            print("  失败: " + str(result.get("error")))
        ports = result.get("ports") or []
        for p in ports:
            print("   " + str(p.get("port")) + "/" + str(p.get("proto")) + "\t"
                  + str(p.get("state")) + "\t" + str(p.get("service")) + "\t" + str(p.get("version")))

        url = pick_url(ip, ports)
        web = collect(url) if url else None
        if web:
            print("   web: " + str(web["status_code"]) + "  " + str(web["server"])
                  + "  标题=" + str(web["title"]) + "  语言=" + str(web["language"]))
        records.append({"ip": ip, "ports": ports, "web": web, "findings": []})

    for record in records:
        raw = []
        for detector in DETECTORS:
            try:
                hit = detector.match(record)
            except Exception as exc:
                print("  [检测异常] " + detector.name + " " + type(exc).__name__)
                continue
            if isinstance(hit, list):
                raw.extend(hit)
            elif hit:
                raw.append(hit)
        kept = normalize(raw)
        record["findings"] = kept
        print("== " + str(record["ip"]) + " 原始 " + str(len(raw)) + " 条，保留 " + str(len(kept)) + " 条")

    out = write_records(records, outdir)
    print("")
    print("[落盘] " + out + "  " + str(os.path.getsize(out)) + " 字节")

    report = render_report(records, outdir, scope_file=path)
    print("[报告] " + report + "  " + str(os.path.getsize(report)) + " 字节")
    return 0


if __name__ == "__main__":
    sys.exit(run())
