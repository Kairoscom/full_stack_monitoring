# Full-Stack Monitoring 全栈监控项目

> 一个跑在 1.7G 小服务器上的完整监控栈：主机指标 + 业务指标 + 告警邮件 + 可视化面板。
> 设计目标：**资源最小化、配置可复现、面试可讲清楚**。

[![Docker](https://img.shields.io/badge/Docker-Compose-blue)]()
[![Prometheus](https://img.shields.io/badge/Prometheus-v2.55-orange)]()
[![Grafana](https://img.shields.io/badge/Grafana-11.2-yellow)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()

---

## 目录

- [项目背景](#项目背景)
- [架构图](#架构图)
- [技术栈](#技术栈)
- [快速启动](#快速启动)
- [目录结构](#目录结构)
- [核心组件说明](#核心组件说明)
- [5 条业务告警](#5-条业务告警)
- [10 条主机告警](#10-条主机告警)
- [Grafana 面板](#grafana-面板)
- [踩过的坑（沉淀为经验）](#踩过的坑沉淀为经验)
- [常见操作](#常见操作)
- [后续可优化点](#后续可优化点)

---

## 项目背景

### 解决的问题
公司有 5 个核心网站（百度/Google/GitHub/自己产品站/支付网关），需要一个"上到下"完整的监控：
- **主机层**：CPU/内存/磁盘/网络是否健康
- **业务层**：网站能否访问、响应多快、SSL 证书是否快过期
- **告警层**：出问题立即发邮件给运维
- **可视化层**：用 Grafana 把数据画成图

### 设计约束（为什么这么设计）
| 约束 | 影响 |
|------|------|
| 服务器只有 1.7G 内存 | 选 Prometheus+Grafana 而非更重的 Zabbix；自研 Exporter 不用 cAdvisor |
| 必须能发邮件 | Alertmanager + QQ SMTP（学生党没钱买企业邮箱） |
| 必须可复现 | 全部容器化（5 个服务）+ 一键 `docker compose up` |
| 必须可面试讲 | 每个组件职责清晰、踩的坑都记在这 |

---

## 架构图

```
┌──────────────────────────────────────────────────────────────┐
│                    Alertmanager (9093)                        │
│                  告警分组 / 抑制 / 静默 / 邮件                  │
└────────────────────▲─────────────────────────────────────────┘
                     │ firing alerts
                     │
┌────────────────────┴─────────────────────────────────────────┐
│                  Prometheus (9090)                            │
│         抓取 / 存储 / 告警规则评估 (15s 周期)                  │
│         ┌──────────┬──────────┬──────────┐                   │
│         │ 主机规则  │ 业务规则  │ 自研规则  │  (alerts/*.yml)  │
│         └──────────┴──────────┴──────────┘                   │
└──────▲──────────────▲──────────────▲─────────────────────────┘
       │ scrape       │ scrape        │ scrape
       │ 15s          │ 15s           │ 30s
       │              │               │
┌──────┴──────┐  ┌────┴────┐  ┌───────┴────────┐
│node-exporter│  │ Grafana │  │ site_check     │
│   (9100)    │  │ (3000)  │  │  自研 Exporter │
│  主机指标   │  │ 可视化  │  │  业务指标 (9877)│
│             │  │         │  │  + SSL 检查    │
└─────────────┘  └────┬────┘  └────────────────┘
                      │ query
                      │ PromQL
                      ▼
                ┌──────────┐
                │  邮件发送  │ ← smtp.qq.com:465
                │  QQ 邮箱  │
                └──────────┘
```

**数据流**：Exporter 暴露指标 → Prometheus 15s 抓一次 → 评估告警规则 → 触发后推给 Alertmanager → 按 receiver 发送邮件 → Grafana 同时拉数据画图。

---

## 技术栈

| 组件 | 版本 | 镜像 | 内存 | 作用 |
|------|------|------|------|------|
| Prometheus | 2.55 | prom/prometheus:v2.55.1 | ~256M | 时序数据库 + 告警规则 |
| Alertmanager | 0.28.1 | prom/alertmanager:v0.28.1 | ~32M | 告警分组/抑制/邮件 |
| Grafana | 11.2 | grafana/grafana:11.2.0 | ~128M | 可视化面板 |
| node-exporter | 1.8.2 | prom/node-exporter:v1.8.2 | ~32M | 主机指标 |
| site_check | 自研 | python:3.9-slim | ~50M | 业务指标（站点可用性）|

**总内存开销**：~500M / 1.7G 可用（30% 占用率）

---

## 快速启动

### 前置条件
- Docker ≥ 20.10
- Docker Compose ≥ 2.0
- 阿里云安全组放行端口：3000（Grafana）、9090（Prometheus）、9093（Alertmanager）、9100（node-exporter）

### 1. 克隆仓库
```bash
git clone <your-repo-url>
cd full_stack_monitoring
```

### 2. 配置邮件（重要！）
编辑 `alertmanager/alertmanager.yml`：
```yaml
global:
  smtp_smarthost: "smtp.qq.com:465"   # 必须用域名，不用 IP
  smtp_from: "your-qq@qq.com"
  smtp_auth_username: "your-qq@qq.com"
  smtp_auth_password: "your-auth-code"  # QQ 邮箱授权码，不是密码
  smtp_require_tls: false
  smtp_hello: "qq.com"
```

### 3. 一键启动
```bash
docker compose up -d
```

### 4. 验证
```bash
# 5 个容器全部 healthy
docker ps

# Prometheus 抓到了 3 个 job
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# Grafana 自动加载 2 个面板
# 打开 http://<your-server>:3000 用 admin/admin 登录
```

---

## 目录结构

```
full_stack_monitoring/
├── docker-compose.yml              # 5 服务编排
├── prometheus/
│   ├── prometheus.yml              # 主配置（3 个 scrape job + 2 个 alert 文件）
│   └── alerts/
│       ├── host_alerts.yml         # 10 条主机告警规则
│       └── business_alerts.yml     # 5 条业务告警规则
├── alertmanager/
│   └── alertmanager.yml            # 邮件发送 + receiver 路由
├── grafana/
│   └── provisioning/
│       ├── datasources/prometheus.yml
│       └── dashboards/
│           ├── host-overview.json  # 主机面板（6 panel）
│           └── site-overview.json  # 业务面板（6 panel）
├── exporters/
│   └── site_check/
│       ├── exporter.py             # 自研 Python exporter（~200 行）
│       ├── Dockerfile
│       ├── requirements.txt
│       └── targets.json            # 监控目标列表
├── scripts/
│   └── collect_container_metrics.sh  # textfile 容器指标采集
├── docs/                            # 踩坑笔记
├── node-exporter-textfile/          # textfile 指标目录（运行时生成）
├── deploy.sh                        # 一键部署脚本
├── LICENSE
└── README.md
```

---

## 核心组件说明

### 1. site_check 自研 Exporter（亮点）

**为什么自研**：node-exporter 只抓主机指标，**不能告诉我"百度能不能访问""SSL 还有几天过期"**。这些业务指标是 node-exporter 给不出来的，所以自己写。

**4 个核心指标**：

| 指标 | 类型 | 含义 |
|------|------|------|
| `site_up` | gauge | 1=可达, 0=不可达 |
| `site_response_time_seconds` | gauge | HTTP 响应时间（秒）|
| `site_status_code` | gauge | HTTP 状态码（0=连接失败）|
| `site_ssl_expiry_days` | gauge | SSL 证书剩余天数（负数=已过期）|

**采集流程**：
```
scheduler_loop() {
    for target in targets.json:
        site_up = HEAD target.url
        site_response_time_seconds = (time_before, time_after)
        site_status_code = response.status_code
        if target.check_ssl:
            site_ssl_expiry_days = (cert.not_after - now).days
        sleep(target.interval)
}
```

### 2. textfile 容器指标

**为什么不用 cAdvisor**：cAdvisor 多吃 50-100M 内存，我们 1.7G 扛不住。

**怎么做的**：
1. shell 脚本 `collect_container_metrics.sh` 每分钟跑一次
2. 用 `docker inspect` 抓所有容器的 `RestartCount`、`State.Running`
3. 写成 Prometheus 文本格式写到 `node-exporter-textfile/` 目录
4. node-exporter 通过 `--collector.textfile.directory` 自动读

### 3. 告警邮件链路

**关键点**：必须用 `smtp.qq.com:465`（**域名，不是 IP**）。  
QQ 邮箱的 SSL 证书只签发给域名，IP 直连会触发 `x509: cannot validate certificate` 错误。

**已踩过的坑**：
- alertmanager 0.27 有个 SMTP 静默失败的 bug（issue #3981）—— **必须用 0.28.1+**
- `repeat_interval` 调试时设的 30s 会导致**真实告警时疯狂发邮件**——生产值用 `4h`

---

## 5 条业务告警

定义在 `prometheus/alerts/business_alerts.yml`：

| # | 告警名 | 触发条件 | 严重度 | 含义 |
|---|--------|---------|--------|------|
| 1 | `SiteDown` | `site_up == 0` 持续 2min | critical | 站点完全不可达 |
| 2 | `SiteSlow` | `site_response_time_seconds > 3` 持续 5min | warning | 站点响应太慢 |
| 3 | `SiteHttpError` | `site_status_code != 200` 持续 2min | warning | HTTP 状态码非 200 |
| 4 | `SslCertExpiringSoon` | `site_ssl_expiry_days < 30` 持续 1h | warning | 证书 30 天内过期 |
| 5 | `SslCertExpiringCritical` | `site_ssl_expiry_days < 7` 持续 10min | critical | 证书一周内过期 |

---

## 10 条主机告警

定义在 `prometheus/alerts/host_alerts.yml`：

| # | 告警名 | 触发条件 | 严重度 |
|---|--------|---------|--------|
| 1 | `HighCPUUsage` | CPU > 80% 持续 5min | warning |
| 2 | `CriticalCPUUsage` | CPU > 95% 持续 2min | critical |
| 3 | `HighMemoryUsage` | 内存 > 85% 持续 5min | warning |
| 4 | `HighDiskUsage` | 根分区 > 85% | warning |
| 5 | `DiskWillFillIn24h` | 预测 24h 内写满 | warning |
| 6 | `HighLoadAverage` | 5min load > CPU 核数 × 2 | warning |
| 7 | `NetworkInterfaceDown` | `node_network_up == 0` 且不是 lo/docker | warning |
| 8 | `HostUnreachable` | Prometheus 抓不到 node-exporter | critical |
| 9 | `ContainerRestarting` | 容器 5min 内重启 ≥ 3 次 | warning |
| 10 | `DockerDaemonDown` | docker.sock 不可达 | critical |

---

## Grafana 面板

启动后自动加载 2 个面板（在 `Monitor` 文件夹下）：

### Host Overview（主机面板）
- CPU 使用率（时序图）
- 内存使用率（时序图）
- 根分区使用率（stat）
- 网络接收速率（时序图）
- 系统 Load (5min avg)（stat）
- **容器启动次数（时序图）** ← textfile 采集

### Site Overview（业务面板）
- 站点可用性（5min 平均）
- 站点响应时间趋势
- SSL 证书剩余天数（最紧急）
- HTTP 状态码分布
- 容器启动次数
- Active 告警数

---

## 踩过的坑（沉淀为经验）

### 1. 镜像源问题
**症状**：`docker pull` 极慢或超时。  
**原因**：docker.io 在国内被限速。  
**正解**：用 `docker.m.daocloud.io/<image>` 前缀（DaoCloud 镜像加速）。

### 2. alertmanager 0.27 静默失败
**症状**：配置看起来全对，日志完全沉默，邮件发不出。  
**原因**：0.27 SMTP 发送存在静默 bug（不报错也不发邮件）。  
**正解**：**升级到 0.28.1+**，并加 `--log.level=debug` 暴露真实错误。

### 3. TLS 证书 IP SAN 验证失败
**症状**：`x509: cannot validate certificate for 183.47.101.192 because it doesn't contain any IP SANs`  
**原因**：QQ SMTP 465 的 SSL 证书只签发给 `smtp.qq.com` 域名，不签发给 IP。  
**正解**：用域名 `smtp.qq.com:465`，让 DNS 解析走 IPv4 拿到正确证书。  
**口诀**：**TLS 用域名，IP 绕道是雷区**。

### 4. `docker compose restart` 不重读 compose
**症状**：改了 healthcheck，`restart` 完没生效。  
**原因**：`restart` 是 stop + start 容器，不重新解析 compose。  
**正解**：改 compose 文件后必须用 `docker compose up -d --force-recreate`。

### 5. exporter 启动读一次 config
**症状**：改了 `targets.json`，exporter 内存里还是旧目标。  
**原因**：`scheduler_loop()` 只在 `if __name__` 启动时读一次。  
**正解**：改 targets.json 后必须 `force-recreate` 容器。

### 6. `restart: unless-stopped` 导致重复告警
**症状**：容器挂了，systemd 拉起来，alertmanager 不停发"重启"邮件。  
**正解**：alertmanager 邮件用 `repeat_interval: 4h`（不是 30s），让它去重。

---

## 常见操作

### 查看所有容器状态
```bash
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

### 查看 Prometheus 抓取目标
```bash
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool
```

### 查看当前告警
```bash
docker exec alertmanager amtool --alertmanager.url=http://localhost:9093 alert query
```

### 查看告警历史发送记录
```bash
docker exec alertmanager amtool --alertmanager.url=http://localhost:9093 nflog
```

### 测试邮件链路
```bash
# 主机 Python SMTP 登录测试
python3 -c "import smtplib; s=smtplib.SMTP_SSL('smtp.qq.com', 465); s.login('your-qq@qq.com', 'your-auth-code'); print('OK')"
```

### 重启特定服务
```bash
docker compose restart <service-name>
# 注意：改 compose 文件后必须用 up -d --force-recreate
```

### 清理 alertmanager 告警历史
```bash
docker exec alertmanager amtool --alertmanager.url=http://localhost:9093 nflog expire
```

---

## 后续可优化点

- [ ] 用 cAdvisor 替代 textfile（要看容器 CPU/内存历史曲线时再上）
- [ ] Alertmanager 加 Webhook 推送到企业微信
- [ ] Prometheus 远程存储（解决 15 天数据保留期问题）
- [ ] exporter 加上 `site_content_hash` 指标，检测页面内容被篡改
- [ ] Grafana 加告警（直接在面板上设阈值）

---

## License

MIT
