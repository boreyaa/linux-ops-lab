import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LEVELS = ("high", "medium", "low", "info")


class BaseDetector:
    name = "base"

    def match(self, target):
        raise NotImplementedError

    def make(self, level, title, evidence):
        if level not in LEVELS:
            raise ValueError("非法等级: " + str(level))
        return {
            "detector": self.name,
            "level": level,
            "title": title,
            "evidence": evidence,
        }
