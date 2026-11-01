# LNMP 部署文档

一台装好系统的 Ubuntu，从零搭到浏览器出现 alpha、beta 两行，全流程约 40 分钟。
系统 Ubuntu，组件 MariaDB + Nginx + PHP-FPM，站点目录 `/var/www/app`，业务库 `appdb`，账号 `app`（仅本机、仅读）。

## 三个为什么

**1. 为什么先 `nginx -t` 再 reload**
`nginx -t` 只校验不加载。语法有错时 reload 被拒绝，nginx 继续用旧配置跑，屏幕上只有一行 `test failed`，很容易误以为改动已生效，之后全朝错误方向排查。用 restart 更糟，进程直接起不来，服务当场停。

**2. 为什么必须删默认站点**
Ubuntu 自带的站点在 `sites-enabled` 里且带 `default_server` 标记，80 端口请求优先落到它。不删，自己写的 `server` 块永远选不中，页面永远是 `Welcome to nginx`，且全程不报错。

**3. 为什么业务账号只给读**
网页只查数据。账号带写权限后，页面被注入或 `db.php` 泄露，攻击者就能直接 `drop database`。只给 `select`，最坏情况从「删库」降级为「读数据」。

## 一、数据库与只读账号

**目的** 装上 MariaDB，关掉匿名用户、测试库、远程 root，再建一个只能读业务库的账号。

**命令**

```bash
sudo apt update
sudo apt install -y mariadb-server
sudo mysql_secure_installation
sudo mysql -e "select user,host,plugin from mysql.user where user='root';"
sudo mysql -e "create database appdb default charset utf8mb4;"
sudo mysql -e "create user 'app'@'localhost' identified by 'App@12345';"
sudo mysql -e "grant select on appdb.* to 'app'@'localhost';"
```

七问回答：root 密码直接回车；切换 unix_socket 答 `Y`；改 root 密码答 `n`；删匿名用户、禁 root 远程、删 test 库、重载权限全 `Y`。

**预期**

```
+------+-----------+-------------+
| user | host      | plugin      |
+------+-----------+-------------+
| root | localhost | unix_socket |
+------+-----------+-------------+
```

建库、建账号、授权三条都返回 `Query OK, 0 rows affected`。

**失败**

- plugin 变成 `mysql_native_password`、`sudo mysql` 不带密码能进 → 第 3 问答错，`sudo mysql -e "alter user 'root'@'localhost' identified via unix_socket; flush privileges;"`
- `ERROR 1698 (28000)` → 不是故障，是 unix_socket 拒绝密码登录的固定错误码，说明加固成功
- 建完账号连不上 → host 写成了 `%` 或 IP，必须是 `localhost`

## 二、网站服务与站点

**目的** 让 80 端口返回自己写的页面，而不是 nginx 欢迎页。

**命令**

```bash
sudo apt install -y nginx
systemctl status nginx --no-pager
sudo mkdir -p /var/www/app
echo "hello app" | sudo tee /var/www/app/index.html
sudo rm -f /etc/nginx/sites-enabled/default
sudo nano /etc/nginx/sites-available/app.conf
sudo ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/app.conf
sudo nginx -t
sudo systemctl reload nginx
curl -I http://127.0.0.1
```

`app.conf` 写入：

```nginx
server {
    listen 80;
    server_name _;
    root /var/www/app;
    index index.html;
    location / { try_files $uri $uri/ =404; }
}
```

保存用 `Ctrl+O` 回车、`Ctrl+X` 退出。

**预期**

```
HTTP/1.1 200 OK
Server: nginx/1.24.0
Content-Type: text/html
```

浏览器打开 `127.0.0.1` 显示 `hello app`。

**失败**

- 还是 `Welcome to nginx` → 默认站点没删，`ls -l /etc/nginx/sites-enabled/` 核对
- 配置怎么改都不生效、`nginx -t` 却是 ok → 漏了 `ln -sf`，nginx 只读 `sites-enabled`
- `nginx -t` 报 `unexpected end of file` → 大括号没配对
- 403 → `sudo chmod -R 755 /var/www/app`

## 三、接后端程序

**目的** 让 `.php` 请求交给 php-fpm 执行，而不是当普通文件返回。

**命令**

```bash
sudo apt install -y php-fpm php-mysql
ls /run/php/
sudo nano /etc/nginx/sites-available/app.conf
sudo nginx -t && sudo systemctl reload nginx
echo "<?php phpinfo();" | sudo tee /var/www/app/info.php
curl -I http://127.0.0.1/info.php
```

第二次进 `app.conf`，在 `location / { ... }` 下面、`server` 的 `}` 之前插入，版本号换成 `ls /run/php/` 看到的那个：

```nginx
    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
    }
```

**预期**

```
HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
X-Powered-By: PHP/8.3.6
```

出现 `X-Powered-By` 说明请求真的走到了后端。

**失败**

- 502 → 只有两个原因：php-fpm 没起（`systemctl status php8.3-fpm`），或 socket 版本号写错（`ls /run/php/`）
- 页面显示 PHP 源码 → `location ~ \.php$` 没写进 `server{}` 里面
- 404 → 文件不在 root 指向的目录，确认 `info.php` 在 `/var/www/app` 下

## 四、建表、插数据、写页面

**目的** 打通最后一层，让页面内容真的来自数据库。

**命令**

```bash
sudo mysql appdb -e "create table t(id int primary key auto_increment, name varchar(20));"
sudo mysql appdb -e "insert into t(name) values('alpha'),('beta');"
sudo mysql -u app -p'App@12345' appdb -e "select * from t;"
sudo nano /var/www/app/db.php
curl http://127.0.0.1/db.php
```

`db.php` 内容：

```php
<?php
$pdo = new PDO('mysql:host=127.0.0.1;dbname=appdb;charset=utf8mb4', 'app', 'App@12345');
foreach ($pdo->query('select name from t') as $row) {
    echo $row['name'], "<br>";
}
```

**预期**

```
Query OK, 2 rows affected
alpha<br>beta<br>
```

**失败**

- `Access denied for user 'app'@'localhost'` → host 写成了 `localhost`，PHP 走 socket 认证失败，改成 `127.0.0.1`
- 页面空白无报错 → 开头加 `error_reporting(E_ALL); ini_set('display_errors', 1);`
- 中文变问号 → 建库与连接串都要 `charset=utf8mb4`
- 出现 `1142`、`DROP command denied` → 只读账号在起作用，预期结果

## 验收

1. `curl -I http://127.0.0.1` 返回 200，不是欢迎页
2. `curl -I http://127.0.0.1/info.php` 返回 200 且带 `X-Powered-By`
3. `curl http://127.0.0.1/db.php` 输出 alpha 和 beta
4. `select user,host,plugin from mysql.user where user='root';` 中 plugin 是 `unix_socket`

## 附：本次踩坑

- 安全初始化第 3 问答了 `Y`，root 的 plugin 从 `unix_socket` 回退成 `mysql_native_password`，数据库等于没有密码。根因是 unix_socket 已接管认证，再设密码就是密码插件覆盖它。处置：`alter user 'root'@'localhost' identified via unix_socket;`
- 习惯：验收看 `mysql.user.plugin` 的取值，不看脚本打印的 `All done!`

