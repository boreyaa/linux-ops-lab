import requests

from collectors.fingerprint import pick_url
from detectors.base import BaseDetector

PATHS = (
    ("/.git/config", "git 配置文件", "medium", "[core]"),
    ("/.svn/entries", "svn 元数据目录", "medium", "dir"),
    ("/.env", "环境变量文件", "high", "="),
    ("/backup.zip", "站点备份压缩包", "high", None),
    ("/www.zip", "站点源码压缩包", "high", None),
    ("/phpinfo.php", "phpinfo 调试页", "low", "PHP Version"),
)


class SensitiveFileDetector(BaseDetector):
    name = "sensitive_file"

    def match(self, target):
        base = pick_url(target.get("ip"), target.get("ports") or [])
        if not base:
            return None
        for path, title, level, marker in PATHS:
            url = base.rstrip("/") + path
            try:
                resp = requests.get(url, timeout=8, verify=False, allow_redirects=False)
            except requests.RequestException:
                continue
            if resp.status_code != 200:
                continue
            body = resp.text[:4096]
            if marker and marker not in body:
                continue
            return self.make(
                level,
                title + " 可未授权读取",
                url + " 状态 200，正文前 4096 字节含特征 " + str(marker),
            )
        return None
