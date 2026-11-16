import logging
import re
import sys

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)

UNKNOWN = "未知"
TIMEOUT = 8

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

LANG_RULES = (
    ("phpsessid", "PHP"),
    ("php", "PHP"),
    ("asp.net_sessionid", "ASP.NET"),
    ("asp.net", "ASP.NET"),
    ("jsessionid", "Java"),
    ("servlet", "Java"),
    ("jsp", "Java"),
    ("express", "Node.js"),
)

HTTP_PORTS = (80, 8080, 8000, 8888)


def read_language(headers):
    evidence = (headers.get("X-Powered-By", "") + " " + headers.get("Set-Cookie", "")).lower()
    if not evidence.strip():
        return UNKNOWN
    for keyword, name in LANG_RULES:
        if keyword in evidence:
            return name
    return UNKNOWN


def read_title(body):
    matched = TITLE_RE.search(body or "")
    if not matched:
        return UNKNOWN
    title = re.sub(r"\s+", " ", matched.group(1)).strip()
    return title or UNKNOWN


def collect(url):
    web = {
        "status_code": UNKNOWN,
        "server": UNKNOWN,
        "title": UNKNOWN,
        "language": UNKNOWN,
    }
    try:
        resp = requests.get(url, timeout=TIMEOUT, allow_redirects=False, verify=False)
    except requests.RequestException as exc:
        log.warning("%s %s", url, type(exc).__name__)
        return web

    web["status_code"] = resp.status_code
    web["server"] = resp.headers.get("Server", "").strip() or UNKNOWN
    web["title"] = read_title(resp.content.decode(resp.apparent_encoding or "utf-8", "ignore"))
    web["language"] = read_language(resp.headers)
    return web


def pick_url(ip, ports):
    opened = [p["port"] for p in ports if p.get("state") == "open"]
    if 80 in opened:
        return "http://" + str(ip)
    if 443 in opened:
        return "https://" + str(ip)
    for port in opened:
        if port in HTTP_PORTS:
            return "http://" + str(ip) + ":" + str(port)
    return None


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.88.100"
    result = collect(target)
    print("目标    " + target)
    print("状态码  " + str(result["status_code"]))
    print("服务器  " + str(result["server"]))
    print("标题    " + str(result["title"]))
    print("语言    " + str(result["language"]))
