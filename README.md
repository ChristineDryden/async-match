# Valhalla League 篮球积分榜

从 [drafted.gg/valhalla-league/results](https://drafted.gg/valhalla-league/results) 抓取篮球赛果，写入远程 MySQL，页面按积分榜样式统计。

## 本地启动

```bash
cd async-match
python3 -m pip install -r requirements.txt
export MYSQL_HOST=127.0.0.1
export MYSQL_USER=dbeaver
export MYSQL_PASSWORD='your-password'
export MYSQL_DATABASE=async_match
python3 -m server.app
```

打开 http://127.0.0.1:8765

## 部署到云服务器 43.155.239.46

MySQL 已经在这台机器上。把代码放到服务器后，用 gunicorn 对外提供 8765 端口。

**1. 从本机上传代码**

```bash
cd /Users/zhang/Desktop
scp -r async-match root@43.155.239.46:/opt/async-match
```

如果 SSH 用户不是 `root`，把用户名改成你的。

**2. SSH 登录服务器**

```bash
ssh root@43.155.239.46
```

**3. 安装依赖（Ubuntu / Debian）**

```bash
apt update
apt install -y python3 python3-venv python3-pip curl
cd /opt/async-match
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

CentOS / Tencent Linux 把 `apt` 换成 `yum` 或 `dnf`。

**4. 先手动跑一次确认能通**

```bash
cd /opt/async-match
source .venv/bin/activate
# 程序和 MySQL 在同一台机，走本机更稳
export MYSQL_HOST=127.0.0.1
export MYSQL_USER=dbeaver
export MYSQL_PASSWORD='your-password'
export MYSQL_DATABASE=async_match
gunicorn --bind 0.0.0.0:8765 --workers 1 --timeout 180 server.app:app
```

本机浏览器打开 http://43.155.239.46:8765/

打不开时检查云厂商安全组 / 防火墙是否放行 **TCP 8765**。

**5. 用 systemd 开机自启（推荐）**

数据库密码写在服务器本地，不要提交到 Git：

```bash
cp /opt/async-match/deploy/async-match.env.example /etc/async-match.env
# 编辑 /etc/async-match.env，填入真实 MYSQL_PASSWORD
chmod 600 /etc/async-match.env
cp /opt/async-match/deploy/async-match.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now async-match
systemctl status async-match
```

常用命令：

```bash
systemctl restart async-match
systemctl stop async-match
journalctl -u async-match -f
```

同步接口最久大约 3 分钟，gunicorn 超时已设为 180 秒。

数据在 MySQL 库 `async_match.basketball_matches`，以比赛 ID 去重。

- **球队 / 选手积分榜**：P、W-L、PCT、GB、L5、STRK
- **快捷时间**：3h / 6h / 12h（快捷键 `1` `2` `3`，`0` 为全部）
- **自定义区间**：选择起止时间后点「应用区间」
- **一键同步**：从库里最新一场的时间点接着爬 drafted.gg，已存在的 ID 不会重复入库

## 同步规则

1. 读取库中 `MAX(played_at)` 作为起点（含该时间点，避免漏掉同一时刻的场次）
2. 从网站最新结果往回翻页，只处理篮球
3. `INSERT IGNORE`，主键是网站 Match ID
4. 翻到整页都早于起点时停止

## 列说明

| 列 | 含义 |
| --- | --- |
| P | 已赛场次 |
| W-L | 胜-负 |
| PCT | 胜率 |
| GB | 落后榜首的场次 |
| L5 | 近 5 场胜负 |
| STRK | 当前连胜 / 连败 |
