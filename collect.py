import socket
import time
from concurrent.futures import ThreadPoolExecutor

PORTS = [22, 80, 443, 3306, 6379, 8080]


def collect_one(host):
    t0 = time.time()
    open_ports = []
    for port in PORTS:
        sock = socket.socket()
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            open_ports.append(port)
        except Exception:
            pass
        finally:
            sock.close()
    return {"host": host, "open": open_ports, "cost": round(time.time() - t0, 2)}


def run(hosts, workers):
    t0 = time.time()
    if workers == 1:
        rows = [collect_one(h) for h in hosts]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(collect_one, hosts))
    return rows, round(time.time() - t0, 2)


def show(tag, rows, total):
    print("=== %s ===" % tag)
    for r in rows:
        ports = ",".join(str(p) for p in r["open"]) or "-"
        print("  %-16s 开放: %-24s 单机耗时 %ss" % (r["host"], ports, r["cost"]))
    print("  %d 台总计 %ss\n" % (len(rows), total))


if __name__ == "__main__":
    hosts = ["127.0.0.1", "127.0.0.1", "192.0.2.1", "10.255.255.1", "192.0.2.2"]

    rows, total = run(hosts, workers=1)
    show("串行 workers=1", rows, total)

    rows, total = run(hosts, workers=8)
    show("并发 workers=8", rows, total)
