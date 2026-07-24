# ============================================
# site_check exporter 镜像
# 作者: wangx
# 基础镜像: python:3.11-slim（Debian 12 兼容,体积小）
# ============================================
FROM docker.m.daocloud.io/library/python:3.11-slim

LABEL maintainer="wangx" \
      description="自研业务 exporter: HTTP/SSL 可用性监控" \
      version="1.0.0"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exporter.py .

RUN useradd -m -u 1000 exporter && \
    chown -R exporter:exporter /app
USER exporter

ENV EXPORTER_PORT=9877 \
    TARGETS_FILE=/app/targets.json

VOLUME ["/app"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9877/metrics', timeout=3)" || exit 1

EXPOSE 9877

CMD ["python", "exporter.py"]
