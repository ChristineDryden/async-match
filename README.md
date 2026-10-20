# Valhalla League 篮球积分榜

从 [drafted.gg/valhalla-league/results](https://drafted.gg/valhalla-league/results) 抓取篮球赛果，写入远程 MySQL。后端提供 JSON API，前端是独立的 Vue 3 应用。

## 目录

```
async-match/
  server/          Flask API、MCP 工具、Grok 聊天
  frontend/        Vue 3 + TypeScript + Axios
  scripts/         抓取脚本与后端测试
  deploy/          systemd 示例
```

本地开发时前后端分开跑。部署时先构建前端，再由 Flask 托管 `frontend/dist`。

## 本地启动

**1. 后端**

```bash
cd async-match
python3 -m pip install -r requirements.txt
export MYSQL_HOST=127.0.0.1
export MYSQL_USER=dbeaver
export MYSQL_PASSWORD='your-password'
export MYSQL_DATABASE=async_match
export XAI_API_KEY='your-xai-api-key'
export AUTH_USERNAME='admin'
export AUTH_PASSWORD='change-me'
python3 -m server.app
```

API：http://127.0.0.1:8765/api/matches

**2. 前端**

```bash
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173 。未登录会停在登录页，默认账号 `admin` / `admin123`，可用 `AUTH_USERNAME` 和 `AUTH_PASSWORD` 改掉。Vite 会把 `/api` 代理到 8765。

## 前端命令

```bash
cd frontend
npm run dev      # 开发
npm run build    # 产出 frontend/dist
npm test         # 积分榜逻辑测试
```

## 部署到云服务器 43.155.239.46

MySQL 已经在这台机器上。把代码放到服务器后，构建前端，再用 gunicorn 对外提供 8765 端口。

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
# 前端构建需要 Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
cd /opt/async-match
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend
npm install
npm run build
```

CentOS / Tencent Linux 把 `apt` 换成 `yum` 或 `dnf`。也可以在本机 `npm run build` 后把 `frontend/dist` 一起上传。

**4. 先手动跑一次确认能通**

```bash
cd /opt/async-match
source .venv/bin/activate
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
- **右下角助手**：Grok 4.6 通过 MCP 工具查库里的积分榜、选手战绩和交锋记录

聊天需要 [xAI API Key](https://console.x.ai)，写入环境变量 `XAI_API_KEY`，不要提交到 Git。模型默认 `grok-4.6`。

MCP 入口：`POST /mcp`（Streamable HTTP）。Grok 聊天走 `POST /api/chat`，后端用同一套工具查 MySQL。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/login` | 登录，写入 HttpOnly 会话 |
| POST | `/api/auth/logout` | 退出 |
| GET | `/api/auth/me` | 当前登录用户 |
| GET | `/api/health` | 探活 |
| GET | `/api/matches` | 全部已入库比赛 |
| POST | `/api/sync` | 增量同步 drafted.gg |
| POST | `/api/chat` | Grok 4.6 比赛分析（会调 MCP 工具） |
| GET/POST | `/mcp` | 比赛数据 MCP 服务 |

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
