import os
import json
import time
import subprocess
import platform
import random
import threading
from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse  # 改为 HTMLResponse 用于伪装页面
import modal

# ========== Modal 配置 ==========
# 从环境变量读取区域，由 GitHub Secrets 传入
DEPLOY_REGION = os.environ.get('DEPLOY_REGION', 'us-east')  # 默认美国东部

# ========== Modal 镜像定义 ==========
image = modal.Image.debian_slim().pip_install(
    "fastapi==0.115.12",
    "pydantic==2.11.7",
    "requests",
    "psutil",
    "uvicorn",
)

app = modal.App("nezha-fastapi-app", image=image)

# ========== FastAPI 实例 ==========
web_app = FastAPI(
    title="Nezha Agent Runner",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# ========== 全局启动控制 ==========
_agent_started = False
_agent_lock = threading.Lock()
_keepalive_started = False
_keepalive_lock = threading.Lock()
_project_url = None

# ========== 伪装页面 HTML ==========
FAKE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oracle Cloud Infrastructure</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            border-radius: 16px;
            padding: 48px;
            max-width: 580px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            text-align: center;
        }
        .logo {
            width: 64px;
            height: 64px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 16px;
            margin: 0 auto 24px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .logo svg { width: 36px; height: 36px; fill: white; }
        <!- 此处省略部分样式，保持与原伪装页面一致，您可自行补充完整 ->
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
            </svg>
        </div>
        <h1>Cloud Services Platform</h1>
        <p class="subtitle">Enterprise-grade cloud infrastructure powering your applications with high availability and global reach.</p>
        <div class="status-badge">
            <span class="dot"></span>
            All Systems Operational
        </div>
        <div class="status-grid">
            <div class="status-card">
                <div class="icon">⚡</div>
                <div class="label">Uptime</div>
                <div class="value">99.97%</div>
            </div>
            <div class="status-card">
                <div class="icon">🌍</div>
                <div class="label">Regions</div>
                <div class="value">12 Active</div>
            </div>
            <div class="status-card">
                <div class="icon">🔒</div>
                <div class="label">Security</div>
                <div class="value">TLS 1.3</div>
            </div>
            <div class="status-card">
                <div class="icon">📊</div>
                <div class="label">Latency</div>
                <div class="value">&lt;50ms</div>
            </div>
        </div>
        <div class="divider"></div>
        <div class="footer">
            <p>&copy; 2025 Cloud Services Platform. All rights reserved.</p>
            <p>Powered by distributed cloud architecture</p>
            <div class="tech-stack">
                <span class="tech-item">Kubernetes</span>
                <span class="tech-item">Docker</span>
                <span class="tech-item">Terraform</span>
                <span class="tech-item">gRPC</span>
            </div>
        </div>
    </div>
</body>
</html>"""

# ========== 辅助函数 ==========
# （以下函数与您的成功代码完全一致，此处省略以节省篇幅，实际使用时请完整保留）
# create_directory, get_system_architecture, download_file, authorize_files,
# write_log, exec_cmd, run_agent, tail_log, find_agent_processes,
# get_project_url, auto_detect_url, add_visit_task, self_keepalive_loop,
# start_keepalive, ensure_agent_started 等函数与成功代码完全相同

# ========== FastAPI 中间件 ==========
@web_app.middleware("http")
async def detect_url_middleware(request: Request, call_next):
    auto_detect_url(request)
    response = await call_next(request)
    return response

# ========== FastAPI 启动事件 ==========
@web_app.on_event("startup")
async def startup_event():
    print("FastAPI startup event fired.")
    print(f"Deploy Region: {DEPLOY_REGION} (from environment)")
    ensure_agent_started()

# ========== FastAPI 路由 ==========
@web_app.get("/")
async def root():
    return HTMLResponse(content=FAKE_HTML)  # 返回伪装页面

@web_app.get("/health")
async def health():
    data = {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.ctime(),
    }
    return Response(content=json.dumps(data), media_type="application/json")

@web_app.get("/status")
async def status():
    processes = find_agent_processes()
    if processes:
        data = {
            "agent_status": "running",
            "processes": processes,
            "process_count": len(processes),
        }
    else:
        data = {
            "agent_status": "not_running",
            "processes": [],
            "process_count": 0,
            "recent_logs": tail_log('/tmp/agent.log', lines=5),
        }
    return Response(content=json.dumps(data), media_type="application/json")

@web_app.get("/logs")
async def logs():
    log_lines = tail_log('/tmp/agent.log', lines=30)
    data = {
        "log_lines": len(log_lines),
        "logs": log_lines,
    }
    return Response(content=json.dumps(data), media_type="application/json")

@web_app.get("/info")
async def info():
    import psutil
    data = {
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "deploy_region": DEPLOY_REGION,  # 显示配置的区域
        "cpu_count": psutil.cpu_count(),
        "memory_total_mb": round(psutil.virtual_memory().total / 1024 / 1024, 2),
        "memory_used_mb": round(psutil.virtual_memory().used / 1024 / 1024, 2),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_total_gb": round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2),
        "disk_used_gb": round(psutil.disk_usage('/').used / 1024 / 1024 / 1024, 2),
        "disk_percent": psutil.disk_usage('/').percent,
        "pid": os.getpid(),
        "cwd": os.getcwd(),
    }
    return Response(content=json.dumps(data), media_type="application/json")

@web_app.get("/keepalive")
async def keepalive_status():
    project_url = get_project_url()
    data = {
        "keepalive_started": _keepalive_started,
        "project_url": project_url or "not detected yet",
        "auto_detected": bool(_project_url),
        "auto_access": os.environ.get('AUTO_ACCESS', 'true'),
        "keepalive_interval": int(os.environ.get('KEEPALIVE_INTERVAL', '120')),
        "recent_logs": [
            line for line in tail_log('/tmp/agent.log', lines=20)
            if 'keepalive' in line.lower() or 'automatic access' in line.lower()
            or 'auto-detected' in line.lower()
        ],
    }
    return Response(content=json.dumps(data), media_type="application/json")

@web_app.get("/restart")
async def restart_agent():
    import psutil
    global _agent_started
    killed = []
    processes = find_agent_processes()
    for proc_info in processes:
        try:
            proc = psutil.Process(proc_info['pid'])
            proc.kill()
            killed.append(proc_info['pid'])
        except Exception:
            pass
    with _agent_lock:
        _agent_started = False
    time.sleep(2)
    ensure_agent_started()
    data = {
        "action": "restart",
        "killed_pids": killed,
        "message": "Agent restart initiated",
    }
    return Response(content=json.dumps(data), media_type="application/json")

# ========== Modal 入口（指定区域，使用环境变量） ==========
@app.function(
    secrets=[modal.Secret.from_name("nezha-secrets")],
    allow_concurrent_inputs=10,
    container_idle_timeout=300,
    region=[DEPLOY_REGION],  # 使用列表形式，支持 broad region
)
@modal.asgi_app()
def fastapi_app():
    return web_app
