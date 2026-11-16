import logging
import time
from concurrent.futures import ThreadPoolExecutor

from collectors.fingerprint import collect

MAX_WORKERS = 20

log = logging.getLogger(__name__)


def collect_one(host):
    try:
        web = collect(host)
        if web["status_code"] == "未知":
            return None
        return {"host": host, "web": web}
    except Exception as exc:
        log.warning("%s %s", host, type(exc).__name__)
        return None


def run_serial(hosts):
    started = time.perf_counter()
    results = [collect_one(h) for h in hosts]
    return time.perf_counter() - started, results


def run_parallel(hosts, max_workers=MAX_WORKERS):
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(collect_one, hosts))
    return time.perf_counter() - started, results
