import requests

from collectors.fingerprint import pick_url
from detectors.base import BaseDetector

PATHS = (
    "/ueditor/controller.php?action=config",
    "/ueditor/php/controller.php?action=config",
    "/ueditor/jsp/controller.jsp?action=config",
    "/ueditor/net/controller.ashx?action=config",
    "/ueditor1_4_3_3-utf8-php/php/controller.php?action=config",
)
MARKERS = ("imageUrlPrefix", "imageMaxSize", "imagePathFormat")


class UeditorDetector(BaseDetector):
    name = "ueditor_unauth"

    def match(self, target):
        base = pick_url(target.get("ip"), target.get("ports") or [])
        if not base:
            return None
        hits = []
        for path in PATHS:
            url = base.rstrip("/") + path
            try:
                resp = requests.get(url, timeout=8, verify=False, allow_redirects=False)
            except requests.RequestException:
                continue
            if resp.status_code != 200:
                continue
            body = resp.text[:20000]
            found = [m for m in MARKERS if m in body]
            if not found:
                continue
            hits.append(self.make(
                "high",
                "UEditor 配置接口未授权访问",
                url + " 状态 200，正文 " + str(len(resp.text)) + " 字节，命中标记 " + ",".join(found),
            ))
        return hits or None
