import ipaddress
import json
import os
import re
import sys
import time
from datetime import datetime

import requests

LOG_PATH = "/var/log/nginx/access.log"
OUT_PATH = "/var/www/admin/index.html"
CACHE_PATH = os.path.expanduser("~/asminsight/data/geo_cache.json")
MAX_ROWS = 500
QUERY_GAP = 1.2

LINE_RE = re.compile(
    r'^(\S+) - \S+ \[([^\]]+)\] "([^"]*)" (\d{3}) (\S+) "([^"]*)" "([^"]*)"'
)


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)


def is_private(ip):
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback
    except Exception:
        return False


def lookup(ip, cache):
    if ip in cache:
        return cache[ip]

    if is_private(ip):
        cache[ip] = "内网或本机"
        return cache[ip]

    try:
        resp = requests.get(
            "http://ip-api.com/json/" + ip,
            params={"lang": "zh-CN", "fields": "status,country,regionName,city,isp"},
            timeout=8,
        )
        data = resp.json()
        if data.get("status") == "success":
            parts = [data.get("country"), data.get("regionName"), data.get("city"), data.get("isp")]
            info = " / ".join([p for p in parts if p])
            cache[ip] = info
            return info
        return "未知"
    except Exception:
        return "查询失败（下次重试）"


def parse_time(raw):
    try:
        dt = datetime.strptime(raw, "%d/%b/%Y:%H:%M:%S %z")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return raw


def read_records():
    records = []
    if not os.path.exists(LOG_PATH):
        return records
    with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = LINE_RE.match(line)
            if not m:
                continue
            ip, ts, request, status, size, referer, ua = m.groups()
            records.append({
                "ip": ip,
                "time": parse_time(ts),
                "request": request[:80],
                "status": status,
                "ua": ua[:60],
            })
    return records


def render(records, cache):
    rows = list(reversed(records))[:MAX_ROWS]

    by_ip = {}
    for item in records:
        by_ip[item["ip"]] = by_ip.get(item["ip"], 0) + 1

    regions = {}
    looked = 0
    for ip in by_ip:
        if ip not in cache and not is_private(ip):
            if looked:
                time.sleep(QUERY_GAP)
            looked += 1
        region = lookup(ip, cache)
        regions[region] = regions.get(region, 0) + by_ip[ip]

    parts = []
    parts.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    parts.append("<title>访问记录</title><style>")
    parts.append('body{font-family:-apple-system,"Microsoft YaHei",sans-serif;max-width:1000px;margin:0 auto;padding:28px 18px;color:#2C2C2A;line-height:1.7;font-size:14px;}')
    parts.append("h1{font-size:21px;font-weight:600;margin:0 0 4px;}")
    parts.append("h2{font-size:15px;font-weight:600;margin:26px 0 10px;padding-left:10px;border-left:3px solid #993C1D;}")
    parts.append(".meta{color:#888780;font-size:12.5px;margin:0 0 22px;}")
    parts.append("table{width:100%;border-collapse:collapse;font-size:12.6px;}")
    parts.append("th{background:#F5F4F0;text-align:left;padding:7px 9px;border-bottom:1px solid #E5E3DC;font-weight:600;}")
    parts.append("td{padding:7px 9px;border-bottom:1px solid #E5E3DC;vertical-align:top;}")
    parts.append("td.mono{font-family:Consolas,monospace;font-size:12px;}")
    parts.append(".s200{color:#0F6E56;font-weight:600;}")
    parts.append("</style></head><body>")
    parts.append("<h1>访问记录</h1>")
    parts.append('<p class="meta">生成时间 ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " · 数据来源 nginx access.log</p>")

    parts.append("<h2>概况</h2><table>")
    parts.append("<tr><th>总请求数</th><th>独立 IP</th><th>显示条数</th></tr>")
    parts.append("<tr><td>" + str(len(records)) + "</td><td>" + str(len(by_ip)) + "</td><td>" + str(len(rows)) + "</td></tr>")
    parts.append("</table>")

    parts.append("<h2>来源分布</h2><table>")
    parts.append("<tr><th>归属地</th><th>请求数</th></tr>")
    for region, count in sorted(regions.items(), key=lambda x: -x[1]):
        parts.append("<tr><td>" + region + "</td><td>" + str(count) + "</td></tr>")
    parts.append("</table>")

    parts.append("<h2>明细</h2><table>")
    parts.append("<tr><th>时间</th><th>IP</th><th>归属地</th><th>状态</th><th>请求</th><th>UA</th></tr>")
    for item in rows:
        status_cls = "s200" if item["status"].startswith("2") else ""
        parts.append(
            "<tr><td>" + item["time"] + '</td><td class="mono">' + item["ip"] + "</td><td>"
            + lookup(item["ip"], cache) + '</td><td class="' + status_cls + '">' + item["status"]
            + '</td><td class="mono">' + item["request"].replace("<", "&lt;") + "</td><td>" + item["ua"].replace("<", "&lt;") + "</td></tr>"
        )
    parts.append("</table>")
    parts.append("</body></html>")
    return "".join(parts)


def main():
    records = read_records()
    if not records:
        print("没有可解析的访问记录")
        return 0
    cache = load_cache()
    html = render(records, cache)
    save_cache(cache)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print("已生成 " + OUT_PATH + "，" + str(len(records)) + " 条记录，缓存 " + str(len(cache)) + " 个 IP")
    return 0


if __name__ == "__main__":
    sys.exit(main())
