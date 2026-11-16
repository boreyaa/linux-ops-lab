import requests

from collectors.fingerprint import pick_url
from detectors.base import BaseDetector

PATH = "/ueditor/controller.php?action=config"
MARKERS = ("imageUrlPrefix", "imageMaxSize", "imagePathFormat")


class UeditorDetector(BaseDetector):
    name = "ueditor_unauth"

    def match(self, target):
        base = pick_url(target.get("ip"), target.get("ports") or [])
        if not base:
            return None
        url = base.rstrip("/") + PATH
        try:
            resp = requests.get(url, timeout=8, verify=False, allow_redirects=False)
        except requests.RequestException:
            return None
        if resp.status_code != 200:
            return None
        body = resp.text[:20000]
        hits = [m for m in MARKERS if m in body]
        if not hits:
            return None
        return self.make(
            "high",
            "UEditor 配置接口未授权访问",
            url + " 状态 200，正文 " + str(len(resp.text)) + " 字节，命中标记 " + ",".join(hits),
        )
