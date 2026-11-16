import ipaddress

import yaml


def load_scope(path="targets.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    return [
        ipaddress.ip_network(str(n).strip(), strict=False)
        for n in cfg.get("allowed_networks", [])
    ]


def in_scope(ip, nets):
    try:
        addr = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return False
    return any(addr in net for net in nets)
