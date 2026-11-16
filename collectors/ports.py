import shutil
import subprocess
import xml.etree.ElementTree as ET

PORTS = "22,80,443,3306,6379,8080"
TIMEOUT = 120


def scan(ip, ports=PORTS, timeout=TIMEOUT):
    result = {"ok": False, "ports": [], "error": ""}

    if not shutil.which("nmap"):
        result["error"] = "nmap 未安装"
        return result

    cmd = ["nmap", "-Pn", "-sV", "-p", ports, "-oX", "-", str(ip)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        result["error"] = "nmap 超时 " + str(timeout) + " 秒"
        return result
    except OSError as exc:
        result["error"] = "nmap 无法执行: " + str(exc)
        return result

    if proc.returncode != 0:
        result["error"] = proc.stderr.strip()[:200] or ("nmap 退出码 " + str(proc.returncode))
        return result

    try:
        root = ET.fromstring(proc.stdout)
    except ET.ParseError as exc:
        result["error"] = "XML 解析失败: " + str(exc)
        return result

    for host in root.findall("host"):
        for port in host.findall("./ports/port"):
            state = port.find("state")
            service = port.find("service")
            parts = []
            if service is not None:
                for key in ("product", "version", "extrainfo"):
                    value = service.get(key)
                    if value:
                        parts.append(value)
            result["ports"].append({
                "port": int(port.get("portid")),
                "proto": port.get("protocol"),
                "state": state.get("state") if state is not None else "",
                "service": service.get("name") if service is not None else "",
                "version": " ".join(parts).strip(),
            })

    result["ok"] = True
    return result


if __name__ == "__main__":
    import json
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    print(json.dumps(scan(target), ensure_ascii=False, indent=2))
