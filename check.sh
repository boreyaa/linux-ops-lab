#!/bin/bash
set -euo pipefail


rc=0
disk=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
mem=$(free | awk '/^Mem:/ {printf "%d", $7/$2*100}')

if [ "$disk" -ge 80 ]; then rc=1; fi
if [ "$mem" -lt 20 ]; then rc=1; fi

echo "disk=${disk}% mem=${mem}% rc=${rc}"
exit $rc

