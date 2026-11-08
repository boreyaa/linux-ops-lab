# 第三周故障处理记录

2026-11-08 | Ubuntu 虚拟机 | 根分区 38G | 内存 3.8G

## 一、磁盘写满

现象
df -h 显示根分区 Use% 从 34% 升到 100%、Avail 归零；此时向 /tmp 写入返回 No space left on device，apt 与日志同时写盘失败。

命令
sudo dd if=/dev/zero of=/tmp/fill bs=1M count=3000
df -h
avail=$(df -BM --output=avail /tmp | tail -1 | tr -dc '0-9')
sudo dd if=/dev/zero of=/tmp/fill2 bs=1M count=$((avail+128))
sudo dd if=/dev/zero of=/tmp/fill3 bs=1M count=100000
df -h
echo test | sudo tee /tmp/probe.txt

执行中看到：第一条写 3G 后仍为 34%，未满；第二条写 24G 后变 36G used / 0 avail / 100%；第三条在 1.7G 处报错，变 38G used / 100%。

原因
count=3000 是固定值，该机可用空间 27G，3G 填不满，所以第一次没有触发故障。按 df 的 Avail 动态取值后写满普通用户可用区。ext4 预留 5%（约 2G）给 root，dd 以 root 运行仍可写入保留区，直到 Size 与 Used 齐平才停止。满盘分两层：普通用户 Avail=0 是第一层，root 也写不进是第二层，中间那段窗口里普通进程失败但 root 服务仍在写。

恢复
sudo rm -f /tmp/fill /tmp/fill2 /tmp/fill3 /tmp/probe.txt
df -h /

删除后回到 8.9G used / 27G avail / 25%。

## 二、端口被占

现象
sudo systemctl start nginx 返回 Job for nginx.service failed because the control process exited with error code，服务起不来；journalctl -u nginx 中可见 bind() to 0.0.0.0:80 failed (98: Address already in use)。

命令
sudo ss -lntp | grep ':80'
sudo systemctl stop nginx
ss -lntp | grep ':80'
sudo python3 -m http.server 80
sudo systemctl start nginx
sudo systemctl status nginx --no-pager

执行中看到：首次直接运行 python3 -m http.server 80 报 OSError: [Errno 98] Address already in use，因为 80 已被运行中的 nginx 占用。先停 nginx、确认 ss 无输出后，python 成功绑定 80，此时再启动 nginx 才复现出启动失败。

原因
80 端口已被监听进程持有，新进程无法绑定同一地址端口，nginx 由 systemd 报告 control process 退出。排查入口是 ss -lntp 看端口持有者，不是配置文件。造这个故障有两个前提必须先满足：目标端口为空、占用者先就位。顺序颠倒就会出现占用者自己绑不上的情况。

恢复
在运行 python 的终端按 Ctrl+C，然后执行：
sudo systemctl restart nginx
sudo ss -lntp | grep ':80'

## 三、配置语法写错

现象
sudo nginx -t 输出 nginx: [emerg] unexpected end of file, expecting "}" in /etc/nginx/nginx.conf:69 与 configuration file test failed。测试期间网站仍可正常访问，因为运行中的 nginx 还在使用内存里的旧配置。

命令
sudo sed -i 's/}/)/' /etc/nginx/sites-available/app.conf
sudo nginx -t
sudo nano /etc/nginx/sites-available/app.conf
sudo sed -i 's/)/}/' /etc/nginx/sites-available/app.conf
sudo nginx -t

原因
sed 's/}/)/' 不带 g 标志，只替换每行第一个匹配，实际改掉的是 location / { try_files $uri $uri/ =404; } 行末的 }。该块失去闭合符号后，后面 location ~ \.php$ 与 server 的闭合符号只能逐层抵消，最外层 server { 始终缺一个配对的 }。nginx 解析到文件末尾仍在等 }，因此报 unexpected end of file。报错位置指向 include 语句所在的 nginx.conf:69，实际坏点在 app.conf。

nginx -t 只做语法检查，不影响正在运行的进程，所以配置坏了网站仍然活着。这类故障不会立刻暴露，属于延迟故障；权限类故障则立刻生效。

恢复
sudo sed -i 's/)/}/' /etc/nginx/sites-available/app.conf
sudo nginx -t
sudo systemctl reload nginx

## 四、文件权限被改

现象
curl -I http://127.0.0.1 返回 HTTP/1.1 403 Forbidden，响应头 Server: nginx/1.18.0 (Ubuntu)。服务在跑、端口通、配置没错，但页面打不开。

命令
sudo chmod 000 /var/www/app/index.html
curl -I http://127.0.0.1
sudo chmod 644 /var/www/app/index.html
curl -I http://127.0.0.1

原因
chmod 000 清空属主、同组、其他人的全部权限位。nginx 的 worker 进程以 www-data 身份运行，读取该文件被内核拒绝，只能返回 403。权限检查发生在每次实际读取文件时，不需要 reload 即立刻生效，这一点与配置类故障相反。

403 与 502 的区别：403 是服务活着但拒绝访问文件，502 是服务活着但后端无响应。前者查权限与路径，后者查上游进程。

恢复
sudo chmod 644 /var/www/app/index.html
curl -I http://127.0.0.1

## 五、内存打满

现象
执行占内存脚本后终端只输出 Killed，没有 Python 报错栈；free -h 显示 used 回落至 283Mi；sudo dmesg | grep -i "killed process" 出现 Out of memory: Killed process 2215 (python3) total-vm:7421500kB, anon-rss:3558868kB, file-rss:2164kB, shmem-rss:0kB, UID:1000 pgtables:14552kB oom_score_adj:0。

命令
python3 -c "a=[]; [a.append('x'*10**7) for _ in range(200)]"
python3 -c "a=[]; [a.append('x'*10**7) for _ in range(1000)]"
free -h
sudo dmesg | grep -i "killed process"

执行中看到：range(200) 累计约 2G，低于该机 3.1G 可用内存，未触发任何异常，命令正常结束。改为 range(1000) 后进程被杀，输出 Killed。

原因
a=[] 配合 a.append 的作用是把字符串留在列表里，阻止 Python 回收，内存才会真正累积，没有这个列表内存一秒钟都不会涨。申请量逼近物理内存上限时，内核 OOM killer 选中该进程并发送 SIGKILL。SIGKILL 不可捕获，进程来不及输出任何信息，bash 只能报告 Killed，所以这类故障没有现场，必须靠 dmesg 事后确认。

日志中 total-vm 是虚拟内存申请量（约 7.1 GiB），anon-rss 是实际驻留的物理内存（约 3.4 GiB），判断吃掉多少内存要看后者。oom_score_adj:0 表示该进程未被调整过被杀的优先级。

内存与磁盘的区别：进程被杀后内核立即回收内存，free 马上回落，不需要手动清理；磁盘满必须手动删文件才能恢复。

恢复
free -h

进程已由内核终止，内存自动归还，无残留文件需要清理。
