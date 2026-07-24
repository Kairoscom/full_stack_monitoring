#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
site_check exporter
作者: wangx
作用: 探测多个站点的可用性, 暴露 Prometheus 指标
设计原则:
  1. 后台线程定时采集,不阻塞 HTTP 服务
  2. targets.json 可热加载,无需重启
  3. 异常分类处理(超时/连接错/SSL错)
  4. 指标标签语义化(url/method)
============================================
"""

import json
import logging
import os
import ssl
import time
from datetime import datetime, timezone
from threading import Lock, Thread

import urllib3
import urllib.request
import urllib.error
from prometheus_client import start_http_server, Gauge, Info

# ===== 日志配置 =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('site_check')

# ===== Prometheus 指标定义 =====
SITE_UP = Gauge(
    'site_up',
    '1 if the site is reachable, 0 otherwise',
    ['url', 'method']
)

SITE_RESPONSE_TIME = Gauge(
    'site_response_time_seconds',
    'HTTP response time in seconds',
    ['url', 'method']
)

SITE_STATUS_CODE = Gauge(
    'site_status_code',
    'HTTP status code (0 means connection failed)',
    ['url', 'method']
)

SITE_SSL_EXPIRY_DAYS = Gauge(
    'site_ssl_expiry_days',
    'Days until SSL certificate expires (negative means expired)',
    ['url']
)

# 全局缓存
targets_cache = []
targets_mtime = 0
cache_lock = Lock()


def load_targets():
    """加载探测目标列表（targets.json）,支持热更新"""
    global targets_cache, targets_mtime

    targets_file = os.environ.get('TARGETS_FILE', '/app/targets.json')

    try:
        current_mtime = os.path.getmtime(targets_file)
    except FileNotFoundError:
        logger.error(f"targets 文件不存在: {targets_file}")
        return

    with cache_lock:
        if current_mtime == targets_mtime and targets_cache:
            return

        try:
            with open(targets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            targets_cache = data.get('sites', [])
            targets_mtime = current_mtime
            logger.info(f"加载 {len(targets_cache)} 个探测目标")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"加载 targets 失败: {e}")


def check_ssl_expiry(url):
    """检查 SSL 证书剩余天数"""
    if not url.startswith('https://'):
        return None

    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(url, timeout=5, context=context) as resp:
            cert = resp.fp.raw._sock.getpeercert()

        not_after = cert['notAfter']
        expiry = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
        expiry = expiry.replace(tzinfo=timezone.utc)
        days_left = (expiry - datetime.now(timezone.utc)).days
        return days_left
    except Exception as e:
        logger.warning(f"SSL 检查失败 {url}: {e}")
        return -1


def probe_site(url, method='GET', timeout=10):
    """探测单个站点"""
    start = time.time()
    ssl_days = None

    try:
        req = urllib.request.Request(url, method=method)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        response = urllib.request.urlopen(req, timeout=timeout)
        status_code = response.status
        response_time = time.time() - start

        ssl_days = check_ssl_expiry(url)

        return status_code, response_time, ssl_days

    except urllib.error.HTTPError as e:
        return e.code, time.time() - start, ssl_days

    except urllib.error.URLError as e:
        logger.warning(f"连接失败 {url}: {e.reason}")
        return 0, time.time() - start, ssl_days

    except Exception as e:
        logger.error(f"探测异常 {url}: {e}")
        return 0, time.time() - start, ssl_days


def update_metrics():
    """更新所有目标的指标"""
    for target in targets_cache:
        url = target.get('url')
        method = target.get('method', 'GET').upper()
        if not url:
            continue

        status, rt, ssl_days = probe_site(url, method)
        up = 1 if 200 <= status < 400 else 0

        SITE_UP.labels(url=url, method=method).set(up)
        SITE_RESPONSE_TIME.labels(url=url, method=method).set(rt)
        SITE_STATUS_CODE.labels(url=url, method=method).set(status)

        if ssl_days is not None:
            SITE_SSL_EXPIRY_DAYS.labels(url=url).set(ssl_days)

        logger.info(f"{method} {url} -> {status} ({rt:.2f}s) up={up}")


def scheduler_loop(interval=30):
    """后台调度循环: 每 30 秒探测一次"""
    logger.info(f"调度器启动, 探测间隔 {interval}s")
    while True:
        try:
            load_targets()
            update_metrics()
        except Exception as e:
            logger.error(f"调度循环异常: {e}", exc_info=True)
        time.sleep(interval)


def main():
    port = int(os.environ.get('EXPORTER_PORT', 9877))

    start_http_server(port)
    logger.info(f"Exporter 启动, 端口 {port}, 访问 /metrics")

    scheduler_thread = Thread(target=scheduler_loop, args=(30,), daemon=True)
    scheduler_thread.start()

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Exporter 退出")


if __name__ == '__main__':
    main()
