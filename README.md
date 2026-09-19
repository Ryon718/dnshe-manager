<p align="center">
<h1 align="center">DNSHE Manager</h1>
<strong>一个现代化、自托管的 DNSHE 第三方域名管理面板</strong>
<br><br>
基于 FastAPI + Vue 3 + SQLite 构建，支持 Docker 一键部署。
<br><br>
<img src="https://img.shields.io/github/license/Ryon718/dnshe-manager">
<img src="https://img.shields.io/github/stars/Ryon718/dnshe-manager">
<img src="https://img.shields.io/github/forks/Ryon718/dnshe-manager">
<img src="https://img.shields.io/github/last-commit/Ryon718/dnshe-manager">
</p>

## 📖 项目简介
DNSHE Manager 是一个基于 DNSHE Open API 开发的第三方、自托管域名管理面板。
它将 DNSHE 的域名管理、DNS 解析、自动续期以及通知功能整合到一个 WebUI 中，让你可以通过一个简单的管理面板完成日常域名维护。

技术栈：
- 前端：Vue 3 + Element Plus
- 后端：FastAPI
- 数据库：SQLite
- 部署：Docker / Docker Compose

> ⚠️ **重要声明**：本项目是由社区开发的第三方开源工具，与 DNSHE 官方没有任何隶属、授权或合作关系。DNSHE 是相关服务及商标的权利人，本项目仅通过其公开 API 提供管理功能。

## ✨ 功能特性

### 🌐 域名管理
- 查看所有已注册子域名
- 显示注册时间、到期时间、剩余天数
- 一键申请新子域名（自动拉取可用根域名）
- 一键手动续期

### 🔧 DNS 解析管理
- 支持全类型记录：A / AAAA / CNAME / TXT / MX / NS / SRV / CAA
- 记录的增删改查
- 表单类型自动联动（MX 显示优先级、SRV 显示端口/权重、CAA 显示标签）
- 域名自定义 NS 服务器委派

### 🔄 自动续期
- 每个域名单独开关自动续期
- 可视化倒计时（显示距离进入 180 天续期窗口的剩余天数）
- 每日凌晨 3 点自动扫描，进入续期窗口自动续 1 年
- 续期成功/失败自动推送通知

### 🔔 多渠道通知
- 钉钉 / 企业微信 / 飞书群机器人 Webhook
- Bark（iOS 推送）
- Server酱（微信推送）
- Telegram Bot（支持自定义代理）

### 🔐 安全机制
- DNSHE API Key 仅后端存储，前端不暴露
- 用户密码 bcrypt 哈希存储，数据库不存明文
- 登录鉴权 + Token 7 天过期
- 连续 5 次登录失败自动封 IP 10 分钟
- 操作日志全记录

## 🚀 快速部署

### Docker Compose（推荐）
创建 `docker-compose.yml`：

```yaml
services:
  dnshe-manager:
    image: ghcr.io/ryon718/dnshe-manager:latest
    container_name: dnshe-manager
    ports:
      - "8100:8080"
    volumes:
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
    restart: unless-stopped
```

启动：
```bash
docker compose up -d
```

访问：`http://你的服务器IP:8100`

### 本地源码构建
```bash
git clone https://github.com/Ryon718/dnshe-manager.git
cd dnshe-manager
docker compose up -d --build
```

## 🔑 首次使用
1. 浏览器打开 `http://你的IP:8100`
2. 默认账号：`admin` / `admin123`
3. 登录后立即在「设置 → 安全设置」修改默认密码
4. 在「设置 → DNSHE 账号管理」添加你的 DNSHE API Key/Secret
5. 可选：配置通知渠道、为长期使用的域名开启自动续期

> 建议不要将默认密码用于公网部署，请修改为 12 位以上强密码。

## 🛡️ 公网部署安全建议
如果将面板部署到公网，建议：
- 前面套 Nginx 反代并启用 HTTPS
- 使用强管理员密码
- 定期更新 Docker 镜像
- 避免直接将管理端口暴露到公网 0.0.0.0
- 家庭内网使用可搭配 WireGuard / Tailscale / ZeroTier 访问

## 📸 界面预览
| 仪表盘 | 域名管理 |
|--------|----------|
| ![仪表盘](screenshots/dashboard.png) | ![域名管理](screenshots/domains.png) |

| DNS 解析管理 | 自动续期 |
|-------------|----------|
| ![DNS解析](screenshots/dns.png) | ![自动续期](screenshots/renewal.png) |

## 📝 更新日志
详细版本更新记录请查看 [CHANGELOG.md](./CHANGELOG.md)

## 🤝 参与贡献
欢迎提交 Bug 修复、功能改进、文档更新。提交 PR 前请先阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)。

如果发现安全漏洞，请不要公开 Issue，参考 [SECURITY.md](./SECURITY.md) 私下报告。

## 📄 License
本项目采用 [MIT](./LICENSE) 协议开源，可自由使用、修改、分发。

## ⭐ 支持项目
如果这个项目对你有帮助，欢迎点个 Star ⭐ 支持一下。

<p align="center">
Made with ❤️ by <a href="https://github.com/Ryon718">Ryon718</a>
</p>
