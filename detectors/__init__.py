from detectors.sensitive import SensitiveFileDetector
from detectors.ueditor import UeditorDetector

DETECTORS = [
    UeditorDetector(),
    SensitiveFileDetector(),
]
