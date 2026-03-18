from flask import Flask, request, render_template_string, jsonify
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, 
    FeedbackRequired, PleaseWaitFewMinutes
)
import os, time, random, json, threading, hashlib

app = Flask(__name__)

# ============ SETUP ============
UPLOAD_FOLDER = "uploads"
LOG_FILE = "logs/live_messages.log"
SESSION_DIR = "sessions"
for d in [UPLOAD_FOLDER, "logs", SESSION_DIR]:
    os.makedirs(d, exist_ok=True)

stop_keys = {}
attack_stats = {
    "total_sent": 0,
    "total_failed": 0,
    "active_threads": 0,
    "start_time": None,
    "accounts_used": 0,
    "blocked_count": 0
}
lock = threading.Lock()

# ============ MEGA HTML TEMPLATE ============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>💀 MR KRIX ULTRA V2 💀</title>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&display=swap" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<style>
    :root {
        --neon-green: #00ff41;
        --neon-red: #ff0055;
        --neon-blue: #00d4ff;
        --neon-purple: #b300ff;
        --neon-yellow: #ffe600;
        --bg-dark: #030303;
        --panel: rgba(10,10,10,0.95);
    }

    * { margin:0; padding:0; box-sizing:border-box; }

    body {
        background: var(--bg-dark);
        color: var(--neon-green);
        font-family: 'Fira Code', monospace;
        min-height: 100vh;
        overflow-x: hidden;
    }

    /* ===== MATRIX RAIN ===== */
    #matrix-canvas {
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        z-index: 0;
        opacity: 0.15;
    }

    /* ===== BOOT SCREEN ===== */
    #boot-screen {
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background: #000;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        transition: opacity 1s;
    }
    #boot-screen.hide { opacity: 0; pointer-events: none; }
    .skull-art {
        color: var(--neon-red);
        font-size: 10px;
        line-height: 1.1;
        white-space: pre;
        text-shadow: 0 0 10px var(--neon-red);
        animation: pulse 1.5s infinite;
    }
    .boot-text {
        color: var(--neon-green);
        margin-top: 20px;
        font-size: 14px;
        animation: blink 0.5s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(1.02); }
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
    }

    /* ===== MAIN CONTAINER ===== */
    .main-container {
        position: relative;
        z-index: 1;
        max-width: 520px;
        margin: 10px auto;
        padding: 15px;
    }

    /* ===== HEADER ===== */
    .header {
        text-align: center;
        padding: 20px 0;
        border-bottom: 1px solid #222;
        margin-bottom: 15px;
    }
    .header h1 {
        font-size: 28px;
        background: linear-gradient(90deg, var(--neon-red), var(--neon-purple), var(--neon-blue), var(--neon-green));
        background-size: 300% 300%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: rgbShift 3s ease infinite;
        text-shadow: none;
    }
    .header .subtitle {
        color: #555;
        font-size: 11px;
        margin-top: 5px;
    }

    @keyframes rgbShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* ===== STATS DASHBOARD ===== */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-bottom: 15px;
    }
    .stat-card {
        background: rgba(0,255,65,0.05);
        border: 1px solid #1a1a1a;
        border-radius: 8px;
        padding: 12px 8px;
        text-align: center;
        transition: 0.3s;
    }
    .stat-card:hover {
        border-color: var(--neon-green);
        box-shadow: 0 0 15px rgba(0,255,65,0.2);
    }
    .stat-number {
        font-size: 22px;
        font-weight: bold;
        color: var(--neon-green);
    }
    .stat-label {
        font-size: 9px;
        color: #666;
        margin-top: 4px;
        text-transform: uppercase;
    }
    .stat-card.danger .stat-number { color: var(--neon-red); }
    .stat-card.info .stat-number { color: var(--neon-blue); }
    .stat-card.warn .stat-number { color: var(--neon-yellow); }

    /* ===== ATTACK MODE SELECTOR ===== */
    .mode-selector {
        display: flex;
        gap: 8px;
        margin-bottom: 15px;
    }
    .mode-btn {
        flex: 1;
        padding: 10px;
        background: #0a0a0a;
        border: 1px solid #222;
        border-radius: 8px;
        text-align: center;
        cursor: pointer;
        transition: 0.3s;
        font-family: 'Fira Code', monospace;
        color: #555;
        font-size: 11px;
    }
    .mode-btn:hover, .mode-btn.active {
        border-color: var(--neon-green);
        color: var(--neon-green);
        box-shadow: 0 0 10px rgba(0,255,65,0.3);
    }
    .mode-btn i { display: block; font-size: 18px; margin-bottom: 5px; }

    /* ===== FORM ===== */
    .form-panel {
        background: var(--panel);
        border: 1px solid #1a1a1a;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .input-group {
        position: relative;
        margin-bottom: 12px;
    }
    .input-group i {
        position: absolute;
        left: 12px;
        top: 50%;
        transform: translateY(-50%);
        color: #444;
        font-size: 14px;
    }
    .input-group input, .input-group textarea {
        width: 100%;
        padding: 12px 12px 12px 40px;
        background: #0a0a0a;
        border: 1px solid #222;
        color: var(--neon-green);
        border-radius: 8px;
        font-family: 'Fira Code', monospace;
        font-size: 12px;
        outline: none;
        transition: 0.3s;
    }
    .input-group input:focus, .input-group textarea:focus {
        border-color: var(--neon-green);
        box-shadow: 0 0 10px rgba(0,255,65,0.2);
    }
    .input-group input::placeholder { color: #333; }

    .file-upload {
        border: 2px dashed #222;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        cursor: pointer;
        transition: 0.3s;
        margin-bottom: 12px;
    }
    .file-upload:hover {
        border-color: var(--neon-green);
        background: rgba(0,255,65,0.03);
    }
    .file-upload i { font-size: 24px; color: #444; }
    .file-upload p { font-size: 11px; color: #444; margin-top: 8px; }
    .file-upload input { display: none; }

    /* ===== BUTTONS ===== */
    .attack-btn {
        width: 100%;
        padding: 14px;
        border: none;
        border-radius: 8px;
        font-family: 'Fira Code', monospace;
        font-size: 14px;
        font-weight: bold;
        cursor: pointer;
        transition: 0.3s;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .btn-launch {
        background: linear-gradient(135deg, var(--neon-green), #00cc33);
        color: #000;
        box-shadow: 0 0 20px rgba(0,255,65,0.3);
    }
    .btn-launch:hover {
        box-shadow: 0 0 40px rgba(0,255,65,0.6);
        transform: translateY(-2px);
    }
    .btn-stop {
        background: linear-gradient(135deg, var(--neon-red), #cc0044);
        color: #fff;
        box-shadow: 0 0 20px rgba(255,0,85,0.3);
        margin-top: 10px;
    }
    .btn-stop:hover {
        box-shadow: 0 0 40px rgba(255,0,85,0.6);
    }

    /* ===== TERMINAL ===== */
    .terminal-window {
        background: #000;
        border: 1px solid #1a1a1a;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 15px;
    }
    .terminal-header {
        background: #111;
        padding: 8px 12px;
        display: flex;
        align-items: center;
        gap: 6px;
        border-bottom: 1px solid #1a1a1a;
    }
    .terminal-dot {
        width: 10px; height: 10px;
        border-radius: 50%;
    }
    .dot-red { background: #ff5f56; }
    .dot-yellow { background: #ffbd2e; }
    .dot-green { background: #27c93f; }
    .terminal-title {
        color: #555;
        font-size: 11px;
        margin-left: 8px;
    }
    .terminal-body {
        padding: 12px;
        height: 280px;
        overflow-y: auto;
        font-size: 11px;
        line-height: 1.6;
    }
    .terminal-body::-webkit-scrollbar { width: 4px; }
    .terminal-body::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }

    .log-success { color: #00ff41; }
    .log-error { color: #ff0055; }
    .log-warn { color: #ffe600; }
    .log-info { color: #00d4ff; }
    .log-system { color: #b300ff; }

    /* ===== STOP KEY DISPLAY ===== */
    .stop-key-box {
        background: rgba(255,230,0,0.05);
        border: 1px solid rgba(255,230,0,0.3);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        margin-bottom: 15px;
        animation: pulse 2s infinite;
    }
    .stop-key-box .key {
        color: var(--neon-yellow);
        font-size: 18px;
        font-weight: bold;
        letter-spacing: 3px;
    }

    /* ===== FOOTER ===== */
    .footer {
        text-align: center;
        padding: 15px;
        color: #333;
        font-size: 10px;
        border-top: 1px solid #111;
    }

    /* ===== GLITCH EFFECT ===== */
    .glitch {
        animation: glitch 2s infinite;
    }
    @keyframes glitch {
        0%, 90%, 100% { transform: translate(0); }
        92% { transform: translate(-2px, 1px); }
        94% { transform: translate(2px, -1px); }
        96% { transform: translate(-1px, -1px); }
        98% { transform: translate(1px, 2px); }
    }

    /* ===== RESPONSIVE ===== */
    @media (max-width: 400px) {
        .stats-grid { grid-template-columns: repeat(2, 1fr); }
        .mode-selector { flex-wrap: wrap; }
        .header h1 { font-size: 22px; }
    }
</style>
</head>
<body>

<!-- MATRIX RAIN CANVAS -->
<canvas id="matrix-canvas"></canvas>

<!-- BOOT SCREEN -->
<div id="boot-screen">
<pre class="skull-art">
    ██████╗ ██╗  ██╗██████╗ ██╗██╗  ██╗
    ██╔══██╗██║ ██╔╝██╔══██╗██║╚██╗██╔╝
    ██████╔╝█████╔╝ ██████╔╝██║ ╚███╔╝
    ██╔═══╝ ██╔═██╗ ██╔══██╗██║ ██╔██╗
    ██║     ██║  ██╗██║  ██║██║██╔╝ ██╗
    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
        💀 ULTRA SYSTEM v2.0 💀
</pre>
<p class="boot-text">[ INITIALIZING ATTACK FRAMEWORK... ]</p>
</div>

<!-- MAIN CONTENT -->
<div class="main-container">

    <!-- HEADER -->
    <div class="header">
        <h1 class="glitch">💀 MR KRIX ULTRA V2 💀</h1>
        <p class="subtitle">[ ADVANCED INSTAGRAM ATTACK FRAMEWORK ]</p>
    </div>

    <!-- LIVE STATS -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-number" id="stat-sent">0</div>
            <div class="stat-label">📤 Sent</div>
        </div>
        <div class="stat-card danger">
            <div class="stat-number" id="stat-failed">0</div>
            <div class="stat-label">❌ Failed</div>
        </div>
        <div class="stat-card info">
            <div class="stat-number" id="stat-speed">0/m</div>
            <div class="stat-label">⚡ Speed</div>
        </div>
        <div class="stat-card warn">
            <div class="stat-number" id="stat-threads">0</div>
            <div class="stat-label">🔥 Active</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="stat-uptime">00:00</div>
            <div class="stat-label">⏱️ Uptime</div>
        </div>
        <div class="stat-card danger">
            <div class="stat-number" id="stat-blocks">0</div>
            <div class="stat-label">🛡️ Blocks</div>
        </div>
    </div>

    <!-- ATTACK MODE -->
    <div class="mode-selector">
        <div class="mode-btn active" onclick="selectMode(this, 'turbo')">
            <i class="fas fa-bolt"></i> TURBO
        </div>
        <div class="mode-btn" onclick="selectMode(this, 'normal')">
            <i class="fas fa-paper-plane"></i> NORMAL
        </div>
        <div class="mode-btn" onclick="selectMode(this, 'stealth')">
            <i class="fas fa-ghost"></i> STEALTH
        </div>
    </div>

    <!-- FORM -->
    <form action="/" method="POST" enctype="multipart/form-data">
    <div class="form-panel">
        <div class="input-group">
            <i class="fas fa-user"></i>
            <input type="text" name="username" placeholder="Instagram Username" required>
        </div>
        <div class="input-group">
            <i class="fas fa-lock"></i>
            <input type="password" name="password" placeholder="Instagram Password" required>
        </div>
        <div class="input-group">
            <i class="fas fa-crosshairs"></i>
            <input type="text" name="recipient" placeholder="Target Username (comma for multi)" required>
        </div>
        <div class="input-group">
            <i class="fas fa-clock"></i>
            <input type="number" name="interval" placeholder="Delay in Seconds" value="30" required>
        </div>
        <div class="input-group">
            <i class="fas fa-skull"></i>
            <input type="text" name="haters_name" placeholder="Hater's Name Tag" required>
        </div>
        <input type="hidden" name="mode" id="selected-mode" value="turbo">

        <div class="file-upload" onclick="document.getElementById('fileInput').click()">
            <i class="fas fa-file-upload"></i>
            <p id="file-label">📁 CLICK TO UPLOAD MESSAGE FILE (.txt)</p>
            <input type="file" id="fileInput" name="message_file" accept=".txt" required
                   onchange="document.getElementById('file-label').textContent = '✅ ' + this.files[0].name">
        </div>

        <button type="submit" class="attack-btn btn-launch">
            <i class="fas fa-rocket"></i> LAUNCH ATTACK 🚀
        </button>
    </div>
    </form>

    {% if sk and sk != 'STOPPED' %}
    <div class="stop-key-box">
        <p style="color:#666; font-size:10px;">🔑 YOUR STOP KEY</p>
        <p class="key">{{ sk }}</p>
    </div>
    {% endif %}

    <!-- TERMINAL -->
    <div class="terminal-window">
        <div class="terminal-header">
            <div class="terminal-dot dot-red"></div>
            <div class="terminal-dot dot-yellow"></div>
            <div class="terminal-dot dot-green"></div>
            <span class="terminal-title">krix@ultra:~/attack$</span>
        </div>
        <div class="terminal-body" id="logBox">
            <span class="log-system">[SYSTEM] MR KRIX ULTRA V2 Initialized...</span><br>
            <span class="log-info">[INFO] Waiting for attack configuration...</span>
        </div>
    </div>

    <!-- STOP FORM -->
    <form action="/stop" method="POST">
        <div class="input-group">
            <i class="fas fa-key"></i>
            <input type="text" name="stop_key" placeholder="Enter Stop Key to Terminate" required>
        </div>
        <button type="submit" class="attack-btn btn-stop">
            <i class="fas fa-skull-crossbones"></i> TERMINATE ATTACK ☠️
        </button>
    </form>

    <div class="footer">
        💀 MR KRIX ULTRA V2 • CODED WITH HATE • 2026 💀
    </div>
</div>

<!-- AUDIO -->
<audio id="sendSound" preload="auto">
    <source src="https://www.soundjay.com/buttons/beep-07a.mp3" type="audio/mpeg">
</audio>

<script>
// ===== MATRIX RAIN =====
const canvas = document.getElementById('matrix-canvas');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

const chars = 'MRKRIXULTRA0123456789@#$%^&*';
const fontSize = 12;
const columns = canvas.width / fontSize;
const drops = Array(Math.floor(columns)).fill(1);

function drawMatrix() {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#00ff41';
    ctx.font = fontSize + 'px monospace';

    for (let i = 0; i < drops.length; i++) {
        const text = chars[Math.floor(Math.random() * chars.length)];
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975)
            drops[i] = 0;
        drops[i]++;
    }
}
setInterval(drawMatrix, 50);
window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
});

// ===== BOOT SCREEN =====
setTimeout(() => {
    document.getElementById('boot-screen').classList.add('hide');
}, 3000);

// ===== MODE SELECTOR =====
function selectMode(el, mode) {
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
    document.getElementById('selected-mode').value = mode;
}

// ===== LIVE LOG FETCHER =====
let lastLogCount = 0;
function fetchLogs() {
    fetch('/get_live_logs').then(r => r.json()).then(data => {
        const box = document.getElementById('logBox');
        let html = '';
        data.logs.forEach(line => {
            let cls = 'log-info';
            if (line.includes('✅') || line.includes('SENT')) cls = 'log-success';
            else if (line.includes('❌') || line.includes('FAIL')) cls = 'log-error';
            else if (line.includes('⚠️') || line.includes('WAIT')) cls = 'log-warn';
            else if (line.includes('🔄') || line.includes('SYSTEM')) cls = 'log-system';
            html += '<div class="' + cls + '">' + line.trim() + '</div>';
        });
        box.innerHTML = html;
        box.scrollTop = box.scrollHeight;

        if (data.logs.length > lastLogCount) {
            try { document.getElementById('sendSound').play(); } catch(e) {}
            lastLogCount = data.logs.length;
        }
    }).catch(() => {});
}

// ===== LIVE STATS FETCHER =====
function fetchStats() {
    fetch('/get_stats').then(r => r.json()).then(s => {
        document.getElementById('stat-sent').textContent = s.total_sent || 0;
        document.getElementById('stat-failed').textContent = s.total_failed || 0;
        document.getElementById('stat-threads').textContent = s.active_threads || 0;
        document.getElementById('stat-blocks').textContent = s.blocked_count || 0;
        document.getElementById('stat-speed').textContent = (s.speed || '0') + '/m';
        document.getElementById('stat-uptime').textContent = s.uptime || '00:00';
    }).catch(() => {});
}

setInterval(fetchLogs, 2000);
setInterval(fetchStats, 3000);
</script>
</body>
</html>
"""

# ============ HELPER FUNCTIONS ============
def log_event(msg):
    with lock:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

def get_session_path(username):
    return os.path.join(SESSION_DIR, f"{username}_session.json")

def smart_login(cl, username, password):
    """Login with session reuse to avoid bans"""
    session_path = get_session_path(username)
    
    # Try loading saved session first
    if os.path.exists(session_path):
        try:
            with open(session_path, "r") as f:
                session_data = json.load(f)
            cl.set_settings(session_data)
            cl.login(username, password)
            log_event(f"✅ SESSION RESTORED: @{username}")
            return True
        except Exception:
            log_event(f"⚠️ Old session expired, fresh login...")

    # Fresh login
    cl.login(username, password)
    
    # Save session for future use
    with open(session_path, "w") as f:
        json.dump(cl.get_settings(), f)
    
    log_event(f"✅ FRESH LOGIN SUCCESS: @{username}")
    return True

def get_delay(mode, base_interval):
    """Smart delay based on attack mode"""
    if mode == "turbo":
        return max(5, base_interval // 3) + random.uniform(1, 3)
    elif mode == "stealth":
        return base_interval * 2 + random.uniform(10, 30)
    else:  # normal
        return base_interval + random.uniform(2, 8)

# ============ ATTACK ENGINE ============
def run_attack(username, password, targets, file_path, interval, haters_name, stop_key, mode):
    global attack_stats
    
    cl = Client()
    cl.delay_range = [2, 5]
    
    # Randomize device fingerprint
    devices = [
        {"app_version": "269.0.0.18.75", "device_model": "SM-G973F", "manufacturer": "samsung"},
        {"app_version": "275.0.0.27.98", "device_model": "Pixel 6", "manufacturer": "Google"},
        {"app_version": "272.0.0.16.73", "device_model": "OnePlus9Pro", "manufacturer": "OnePlus"},
        {"app_version": "270.0.0.15.80", "device_model": "Mi11", "manufacturer": "Xiaomi"},
    ]
    device = random.choice(devices)
    device["android_version"] = random.randint(26, 33)
    device["android_release"] = str(random.randint(10, 14))
    cl.set_device(device)

    try:
        log_event(f"🔄 [SYSTEM] Connecting as @{username}...")
        smart_login(cl, username, password)
        
        with lock:
            attack_stats["active_threads"] += 1
            attack_stats["accounts_used"] += 1
            if not attack_stats["start_time"]:
                attack_stats["start_time"] = time.time()

        # Resolve all targets
        target_ids = []
        target_list = [t.strip() for t in targets.split(",")]
        for t in target_list:
            try:
                uid = cl.user_id_from_username(t)
                target_ids.append((t, uid))
                log_event(f"🎯 TARGET LOCKED: @{t} (ID: {uid})")
            except Exception:
                log_event(f"❌ TARGET NOT FOUND: @{t}")

        if not target_ids:
            log_event("❌ NO VALID TARGETS! Attack aborted.")
            return

        with open(file_path, 'r') as f:
            messages = [l.strip() for l in f if l.strip()]

        if not messages:
            log_event("❌ MESSAGE FILE IS EMPTY!")
            return

        log_event(f"💀 ATTACK MODE: {mode.upper()} | TARGETS: {len(target_ids)} | MESSAGES: {len(messages)}")
        log_event(f"🚀 ====== ATTACK STARTED ======")

        round_num = 0
        while not stop_keys.get(stop_key):
            round_num += 1
            log_event(f"🔁 --- ROUND {round_num} ---")
            
            for msg in messages:
                if stop_keys.get(stop_key):
                    break

                for target_name, target_id in target_ids:
                    if stop_keys.get(stop_key):
                        break
                        
                    full_msg = f"{haters_name} {msg}"
                    try:
                        cl.direct_send(full_msg, user_ids=[target_id])
                        with lock:
                            attack_stats["total_sent"] += 1
                        log_event(f"✅ SENT → @{target_name}: {full_msg[:50]}...")
                        
                    except FeedbackRequired:
                        with lock:
                            attack_stats["blocked_count"] += 1
                        log_event("⚠️ FEEDBACK BLOCK! Auto-cooldown 30 min...")
                        time.sleep(1800)
                        
                    except PleaseWaitFewMinutes:
                        log_event("⚠️ RATE LIMITED! Cooling down 10 min...")
                        time.sleep(600)
                        
                    except LoginRequired:
                        log_event("🔄 SESSION EXPIRED! Re-logging...")
                        try:
                            smart_login(cl, username, password)
                        except:
                            log_event("❌ RE-LOGIN FAILED! Attack stopped.")
                            return
                            
                    except Exception as e:
                        with lock:
                            attack_stats["total_failed"] += 1
                        log_event(f"❌ FAILED → @{target_name}: {str(e)[:60]}")
                        time.sleep(5)

                    delay = get_delay(mode, interval)
                    time.sleep(delay)

        log_event("☠️ ====== ATTACK TERMINATED ======")

    except ChallengeRequired:
        log_event("❌ CHALLENGE REQUIRED! Open Instagram app and verify first!")
    except Exception as e:
        log_event(f"❌ FATAL ERROR: {str(e)}")
    finally:
        with lock:
            attack_stats["active_threads"] = max(0, attack_stats["active_threads"] - 1)

# ============ FLASK ROUTES ============
@app.route("/", methods=["GET", "POST"])
def index():
    sk = None
    if request.method == "POST":
        sk = f"KRIX-{random.randint(1000, 9999)}"
        stop_keys[sk] = False

        file = request.files["message_file"]
        path = os.path.join(UPLOAD_FOLDER, f"{int(time.time())}_{file.filename}")
        file.save(path)

        t = threading.Thread(target=run_attack, args=(
            request.form["username"],
            request.form["password"],
            request.form["recipient"],
            path,
            int(request.form["interval"]),
            request.form["haters_name"],
            sk,
            request.form.get("mode", "normal")
        ), daemon=True)
        t.start()
        
        log_event(f"💀 [SYSTEM] Attack launched by operator! Key: {sk}")

    return render_template_string(HTML_TEMPLATE, sk=sk)

@app.route("/get_live_logs")
def get_live_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        return jsonify(logs=lines[-30:])
    return jsonify(logs=["[SYSTEM] Waiting for attack..."])

@app.route("/get_stats")
def get_stats():
    uptime = "00:00"
    speed = 0
    if attack_stats["start_time"]:
        elapsed = time.time() - attack_stats["start_time"]
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        uptime = f"{mins:02d}:{secs:02d}"
        if elapsed > 0:
            speed = round(attack_stats["total_sent"] / (elapsed / 60), 1)

    return jsonify(
        total_sent=attack_stats["total_sent"],
        total_failed=attack_stats["total_failed"],
        active_threads=attack_stats["active_threads"],
        blocked_count=attack_stats["blocked_count"],
        speed=speed,
        uptime=uptime
    )

@app.route("/stop", methods=["POST"])
def stop():
    sk = request.form.get("stop_key")
    if sk in stop_keys:
        stop_keys[sk] = True
        log_event(f"☠️ [SYSTEM] Attack terminated! Key: {sk}")
    return render_template_string(HTML_TEMPLATE, sk="STOPPED")

# ============ START SERVER ============
if __name__ == "__main__":
    open(LOG_FILE, "w").close()
    attack_stats["start_time"] = None
    print("""
    ╔══════════════════════════════════════╗
    ║   💀 MR KRIX ULTRA V2 LOADED 💀     ║
    ║   🌐 http://0.0.0.0:20979           ║
    ║   ⚡ READY TO DESTROY               ║
    ╚══════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=20979, debug=False)
