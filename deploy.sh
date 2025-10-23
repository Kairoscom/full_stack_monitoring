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
