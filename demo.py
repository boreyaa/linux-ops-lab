import time
from concurrent.futures import ThreadPoolExecutor

def task(n):
    time.sleep(1)
    return n * n

with ThreadPoolExecutor(max_workers=4) as ex:
    print(list(ex.map(task, range(8))))
