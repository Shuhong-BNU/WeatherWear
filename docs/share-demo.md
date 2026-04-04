# WeatherWear 公网分享（方案 A）

这份说明对应“本机继续使用 + Cloudflare Quick Tunnel 公网分享”的临时 demo 方案。

## 适用场景

- 你想让别人通过浏览器访问你的 demo
- 你自己仍然继续在本机使用
- 你不想先租服务器

## 前提条件

- Windows 本机可以正常启动 WeatherWear
- 演示期间电脑保持开机联网
- 已安装 `cloudflared`

## 一次性准备

1. 安装 Python 依赖
2. 安装前端依赖
3. 安装 `cloudflared`，并确保命令在 PATH 中可用

## 启动公网分享

```powershell
.\.venv\Scripts\python.exe scripts/share_demo.py
```

脚本会自动：

- 复用正在运行的 WeatherWear；如果没启动，会先启动本机前后端
- 读取 `.runtime/ports.json` 中的前端端口
- 如果前端开发服务器起不来，但 `frontend/dist` 已存在，则自动退回到“由 FastAPI 同时托管前端页面”的模式
- 启动 Cloudflare Quick Tunnel
- 打印：
  - 本机前端地址
  - 本机 API 地址
  - 公网分享链接
  - 当前运行模式

## 访问方式

- 你自己继续访问本机地址，例如 `http://127.0.0.1:5173`
- 别人访问脚本输出的 Cloudflare HTTPS 链接

## 停止公网分享

只关闭公网分享，保留本机应用：

```powershell
.\.venv\Scripts\python.exe scripts/share_demo_down.py
```

同时关闭公网分享和本机应用：

```powershell
.\.venv\Scripts\python.exe scripts/share_demo_down.py --stop-app
```

## 运行信息

- 分享信息：`.runtime/share-demo.json`
- Tunnel PID：`.runtime/tunnel.pid`
- Tunnel 日志：`.runtime/logs/tunnel.log`

## 注意事项

- 这是临时分享方案，不是正式生产部署
- 你关机、断网或关闭 tunnel 后，别人就无法访问
- Cloudflare Quick Tunnel 链接可能在重启后变化
- 本地历史、收藏和日志仍然保存在你的机器上
