# asmsight 四层结构

## collectors/

采集层。只负责从目标取回原始数据，不做任何判断，不写任何范围校验。

- ports.py：`scan(ip)` -> `{"ok": bool, "ports": [], "error": str}`
  端口项含 port、proto、state、service、version。
- fingerprint.py：`collect(url)` -> `{"status_code", "server", "title", "language"}`
  另提供 `pick_url(ip, ports)`，按开放端口拼出 Web 地址。
- batch.py：`run_serial(hosts)` 与 `run_parallel(hosts, max_workers=20)`，均返回 `(耗时秒数, 结果列表)`。失败项为 `None`。

## detectors/

判断层。每个检测器继承 BaseDetector，实现 `match(target)`，命中返回一条 finding，未命中返回 None。

finding 统一四个键：detector、level、title、evidence。

等级四档：high、medium、low、info。

## report/

报告层。render.py 用 jinja2 渲染 tpl.html，autoescape 必须开启。

## main.py

入口。范围校验只在 main.py，且必须先全量校验完再发任何请求。越界则退出码 1。

## 每台目标的结果结构

```yaml
ip: 字符串
ports: 列表，每项含 port/proto/state/service/version
web: 对象，含 status_code/server/title/language
findings: 列表，每项含 detector/level/title/evidence
```
