# DNSHE Manager

一个轻量自托管的 DNSHE 免费域名管理 WebUI，基于 FastAPI + Vue3 + SQLite 构建，Docker 一键部署。

## ✨ 功能特性

- 📊 **仪表盘**：域名总数统计、配额使用进度条、彩色状态标签
- 🌐 **域名管理**：
  - 一键查看所有子域名、注册时间、到期时间、剩余天数
  - 申请新子域名（自动拉取可用根域名列表）
  - 一键续期
- 🔧 **DNS 解析管理**：
  - 支持 A / AAAA / CNAME / TXT / MX / NS / SRV / CAA 全记录类型
  - 记录的增删改查，表单类型联动（MX/SRV/CAA 自动显示对应字段）
  - 域名委派（自定义 NS 服务器）
- 🔄 **自动续期**：
  - 每个域名单独开关自动续期
  - 可视化倒计时（显示距离进入 180 天续期窗口还有多少天）
  - 每天凌晨自动扫描，进入续期窗口自动续 1 年
- 🔔 **多渠道通知**：续期成功/失败自动推送
  - 钉钉/企业微信/飞书群机器人
  - Bark（iOS 推送）
  - Server酱（微信推送）
  - Telegram Bot（支持自定义代理）
- 📋 **操作日志**：所有手动/自动操作完整记录，成功失败一目了然
- 🔒 **安全**：API Key 仅后端存储，前端不暴露；密码密文输入；删除配置二次验证码确认

## 🚀 部署方法

### 准备工作
1. 先在 [DNSHE 客户区](https://my.dnshe.com/) 创建 API 密钥（免费域名管理 → API管理 → 创建）

### Docker Compose 部署

1. 新建 `docker-compose.yml`：
```yaml
services:
  dnshe-manager:
    build: .
    container_name: dnshe-manager
    ports:
      - "8100:8080"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

2. 新建 `Dockerfile`：
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
EXPOSE 8080
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

3. 启动：
```bash
docker-compose up -d --build
```

4. 打开浏览器访问 `http://你的IP:8100`，在设置页填入你的 API Key/Secret 即可使用。

## 📝 说明
- 本项目为第三方非官方工具，与 DNSHE 官方无关
- 免费版 API 不支持通过 API 删除子域名，如需删除请前往 DNSHE 官方后台操作
- 默认每小时 API 调用有限速，本项目已做了本地缓存，不会超限

## 📄 License
MIT
