个人技术监控中心

## 服务器购买以及配置

## GitHub部署

## 服务器部署git，连接github

### 安装git

系统：centos Linux version_7(cat /etc/os_release)

### 配置git

#### 安装：sudo yum install git -y

#### 建立本地连接与github

生成密钥：ssh -keygen -t rsa -b 4096 -C"264056571@qq.com"

复制公钥：cat ~/ .ssh/id_rsa/pub 到new ssh连接
建立连接：git clone git@github.com:kairoscom/repository.git

## 项目初始化部署

### 进入项目目录

```
cd full_stack_monitoring
```

```
mkdir -p {frontend,backend/scripts,backend/config,tests/automation,docs,logs}
创建前端与后端仓库
touch README.md .gitignore deploy.sh backend/config/monitoring.conf
```

### 文件解释

.gitignore告诉 Git“哪些文件 / 目录不要上传到仓库

README.md项目 “说明书”

deploy.sh部署脚本（简化项目上线流程）

backend/config/monitoring.conf后端核心监控配置文件（存放监控规则的 “规则表”）
mv文件修改操作
cd进入文件操作

touch创建文件操作

ls查看文件操作

mkdir文件夹创建操作

 cat读取输入，并且，输出内容配合重定向就是写入就是“>”这个符号，直到<<'EOF'结束

### 构建项目骨架

去除掉不需要上传的文件：日志文件log 配置文件backend 系统文件 临时文件 环境变量

```
# 创建专业的.gitignore
cat > .gitignore << 'EOF'
# 日志文件
logs/
*.log

# 敏感配置
backend/config/*.conf
!backend/config/*.example

# 系统文件
.DS_Store
Thumbs.db

# 临时文件
*.tmp
*.temp

# 环境变量
.env
EOF
```

 chmod +x 【文件名】添加可执行权限的
创建一键部署脚本

```
# 编写部署脚本
cat > deploy.sh << 'EOF'
#!/bin/bash
echo "🚀 开始部署全栈监控系统..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "安装Docker..."
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# 部署监控组件
echo "部署Prometheus..."
docker run -d -p 9090:9090 \
    --name prometheus \
    -v $(pwd)/backend/config/prometheus.yml:/etc/prometheus/prometheus.yml \
    prom/prometheus

echo "部署Grafana..."
docker run -d -p 3000:3000 \
    --name grafana \
    grafana/grafana

echo "部署Node Exporter（系统监控）..."
docker run -d -p 9100:9100 \
    --name node-exporter \
    prom/node-exporter

echo "✅ 部署完成！"
echo "📊 Grafana: http://$(curl -s ifconfig.me):3000 (admin/admin)"
echo "📈 Prometheus: http://$(curl -s ifconfig.me):9090"
echo "🖥 Node Exporter: http://$(curl -s ifconfig.me):9100"
EOF

chmod +x deploy.sh
```

步骤三创建prometheus配置文件

```
# 创建配置目录
mkdir -p backend/config

# 编写基础配置
cat > backend/config/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF
```

步骤四：创建专业的readme

步骤五：提交git
git add

git commit

git push

```
git push -u origin main
```

## 总结多次出错原因

**sudo执行权限失误**

解决方案：sudo usermod -aG（追加a加入G） docker（docker组） $USER （代表当前用户）检验：docker ps 查看基础命令

ls （查看目录）-l （长格式）-a（显示所有文件）

**vpn问题**

**安全组问题**

谨记新手坑ip为公网ip不是自己本地ip，而且单个公网ip要用****/32

## 成功进入 Grafana prometheus node exporter

Grafana：监控可视化面板http://服务器IP:3000

用户admin 密码 已重置：Grafana123456

Prometheus ：监控数据的 “存储中心http://服务器IP:9090

Node Exporter 是服务器数据的 “采集员”（访问地址 `http://服务器IP:9100）

已完成目标：

- Linux云服务器环境配置
- Docker容器化部署
- Prometheus + Grafana + Node Exporter 完整监控栈
- GitHub项目仓库管理
- 阿里云安全组配置
- 服务访问验证



## ai项目提问环节

话术：

## 保持项目活跃

定期更新项目

```
git add .
git commit -m "feat: 添加监控告警配置"
git push
```



## 下一步计划

深度掌控监控系统





