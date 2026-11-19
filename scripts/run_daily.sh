#!/bin/bash
export PATH=/home/bore/.local/bin:/usr/local/bin:/usr/bin:/bin
export HOME=/home/bore

APP=/home/bore/asminsight
OUT=/var/www/reports
LOG=$APP/logs/cron.log

echo "===== $(date '+%F %T %Z') 开始 =====" >> "$LOG"

cd "$APP" || { echo "cd 失败: $APP" >> "$LOG"; exit 1; }

"$APP/.venv/bin/python" main.py --targets targets.server.yaml --out "$OUT/" >> "$LOG" 2>&1
rc=$?

if [ $rc -eq 0 ]; then
    cd "$OUT" || exit 1
    ln -sf "$(ls -t report_*.html | head -1)" report.html
    echo "软链已更新 -> $(readlink report.html)" >> "$LOG"
else
    echo "运行失败，退出码 $rc" >> "$LOG"
fi

echo "===== $(date '+%F %T %Z') 结束 退出码 $rc =====" >> "$LOG"
exit $rc
