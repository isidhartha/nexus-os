const API = 'http://localhost:8000';
let ws = null;
let voiceActive = false;
let commandHistory = [];

// ---- CLOCK ----
function updateClock() {
  const now = new Date();
  document.getElementById('sysTime').textContent = now.toLocaleTimeString('en-US', { hour12: false });
  document.getElementById('sysDate').textContent = now.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' });
  // Mock system stats
  document.getElementById('cpuVal').textContent = (20 + Math.random() * 30).toFixed(0);
  document.getElementById('memVal').textContent = (40 + Math.random() * 20).toFixed(0);
}
setInterval(updateClock, 1000);
updateClock();

// ---- WEBSOCKET ----
function connectWS() {
  try {
    ws = new WebSocket('ws://localhost:8000/ws/nexus');
    ws.onopen = () => {
      setNexusStatus(true);
      setOrbActive(true);
      showToast('NEXUS ONLINE', 'success');
      logToOrb('NEXUS ONLINE');
    };
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === 'command_result' || msg.type === 'response') {
          displayResponse(msg.result || msg.message || JSON.stringify(msg));
        } else if (msg.type === 'connected') {
          setNexusStatus(true);
        } else if (msg.type === 'error') {
          showToast(msg.message || 'Error', 'error');
        }
      } catch { /* ignore malformed */ }
    };
    ws.onerror = () => setNexusStatus(false);
    ws.onclose = () => {
      setNexusStatus(false);
      setOrbActive(false);
      setTimeout(connectWS, 5000);
    };
  } catch { setNexusStatus(false); }
}

function setNexusStatus(online) {
  const badge = document.getElementById('nexusBadge');
  badge.textContent = online ? '● ONLINE' : '● OFFLINE';
  badge.style.color = online ? '#00ff88' : '#ef4444';
  document.getElementById('orbStatus').textContent = online ? 'ACTIVE' : 'STANDBY';
}

function setOrbActive(active) {
  const core = document.getElementById('orbCore');
  if (active) core.classList.add('active');
  else core.classList.remove('active');
}

function logToOrb(msg) {
  document.getElementById('orbStatus').textContent = msg;
}

// ---- COMMAND INPUT ----
function handleCommandKey(e) {
  if (e.key === 'Enter') sendCommand();
  if (e.key === 'ArrowUp' && commandHistory.length > 0) {
    document.getElementById('commandInput').value = commandHistory[commandHistory.length - 1];
  }
}

async function sendCommand() {
  const input = document.getElementById('commandInput');
  const cmd = input.value.trim();
  if (!cmd) return;

  input.value = '';
  commandHistory.push(cmd);
  addToHistory(cmd, null);
  logToOrb('PROCESSING…');
  setOrbActive(true);

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'command', command: cmd }));
  } else {
    // Fallback to REST
    try {
      const r = await fetch(`${API}/api/v1/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      displayResponse(data.response || data.result || JSON.stringify(data));
    } catch (e) {
      displayResponse(`Error: ${e.message}`);
      showToast(`Command failed: ${e.message}`, 'error');
    }
  }
}

function displayResponse(text) {
  const resp = document.getElementById('lastResponse');
  resp.className = 'text-sm text-blue-200 font-mono leading-relaxed';
  resp.textContent = '';
  logToOrb('RESPONDING…');
  // Typewriter effect
  let i = 0;
  const txt = typeof text === 'string' ? text : JSON.stringify(text, null, 2);
  const interval = setInterval(() => {
    resp.textContent += txt[i++];
    if (i >= txt.length) {
      clearInterval(interval);
      logToOrb('READY');
      setOrbActive(false);
      // Update last history item with response
      const items = document.querySelectorAll('.history-item');
      if (items.length > 0) {
        const last = items[items.length - 1];
        const respDiv = last.querySelector('.resp');
        if (respDiv) respDiv.textContent = txt.substring(0, 80) + (txt.length > 80 ? '…' : '');
      }
    }
  }, 15);
}

function addToHistory(cmd, resp) {
  const container = document.getElementById('commandHistory');
  if (container.querySelector('.text-blue-400\\/30')) container.innerHTML = '';
  const item = document.createElement('div');
  item.className = 'history-item';
  item.innerHTML = `<div class="cmd">&gt; ${cmd}</div><div class="resp">${resp || '…'}</div>`;
  container.appendChild(item);
  container.scrollTop = container.scrollHeight;
}

// ---- VOICE ----
function toggleVoice() {
  voiceActive = !voiceActive;
  const btn = document.getElementById('voiceBtn');
  const icon = document.getElementById('voiceIcon');
  const label = document.getElementById('voiceLabel');

  if (voiceActive) {
    icon.className = 'fas fa-stop text-3xl';
    label.textContent = 'LISTENING…';
    btn.classList.add('listening');
    setOrbActive(true);
    // Start voice
    fetch(`${API}/api/v1/voice/start`, { method: 'POST' }).catch(() => {});
    showToast('Voice mode activated', 'info');
  } else {
    icon.className = 'fas fa-microphone text-3xl';
    label.textContent = 'TAP TO SPEAK';
    btn.classList.remove('listening');
    setOrbActive(false);
    fetch(`${API}/api/v1/voice/stop`, { method: 'POST' }).catch(() => {});
  }
}

// ---- SMART HOME ----
async function loadDevices() {
  const container = document.getElementById('deviceGrid');
  try {
    const r = await fetch(`${API}/api/v1/iot/devices`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const devices = await r.json();
    container.innerHTML = '';
    (Array.isArray(devices) ? devices : devices.devices || []).slice(0, 6).forEach(dev => {
      const item = document.createElement('div');
      item.className = 'flex items-center justify-between gap-2 py-1.5';
      const isOn = dev.state === 'on' || dev.value === true || dev.status === 'active';
      item.innerHTML = `
        <div class="flex items-center gap-2">
          <i class="fas fa-${dev.type === 'light' ? 'lightbulb' : dev.type === 'thermostat' ? 'temperature-half' : 'plug'} text-yellow-400 text-xs w-4"></i>
          <span class="text-xs text-slate-300 font-mono">${dev.name || dev.id}</span>
        </div>
        <button class="device-toggle ${isOn ? 'on' : ''}" onclick="toggleDevice('${dev.id || dev.name}', this)"></button>
      `;
      container.appendChild(item);
    });
    if (container.children.length === 0) renderMockDevices(container);
  } catch { renderMockDevices(container); }
}

function renderMockDevices(container) {
  const devices = [
    { name: 'Living Room Light', type: 'light', on: true },
    { name: 'Bedroom Light', type: 'light', on: false },
    { name: 'Thermostat', type: 'thermostat', on: true },
    { name: 'AC Unit', type: 'plug', on: false },
  ];
  container.innerHTML = '';
  devices.forEach(dev => {
    const item = document.createElement('div');
    item.className = 'flex items-center justify-between gap-2 py-1.5';
    item.innerHTML = `
      <div class="flex items-center gap-2">
        <i class="fas fa-${dev.type === 'light' ? 'lightbulb' : dev.type === 'thermostat' ? 'temperature-half' : 'plug'} text-yellow-400 text-xs w-4"></i>
        <span class="text-xs text-slate-300 font-mono">${dev.name}</span>
      </div>
      <button class="device-toggle ${dev.on ? 'on' : ''}" onclick="toggleDevice('${dev.name}', this)"></button>
    `;
    container.appendChild(item);
  });
}

async function toggleDevice(deviceId, btn) {
  const isOn = btn.classList.contains('on');
  btn.classList.toggle('on');
  try {
    await fetch(`${API}/api/v1/iot/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_id: deviceId, action: isOn ? 'off' : 'on' })
    });
  } catch { showToast('Device control failed', 'error'); }
}

// ---- MEMORY ----
async function loadMemory() {
  const container = document.getElementById('memoryList');
  try {
    const r = await fetch(`${API}/api/v1/memory`);
    if (!r.ok) throw new Error();
    const data = await r.json();
    const entries = Array.isArray(data) ? data : data.entries || [];
    container.innerHTML = '';
    entries.slice(0, 5).forEach(m => {
      const item = document.createElement('div');
      item.className = 'memory-item';
      item.textContent = m.content || m.text || JSON.stringify(m);
      container.appendChild(item);
    });
    if (entries.length === 0) container.innerHTML = '<div class="text-blue-400/30 italic text-xs">No memories stored</div>';
  } catch {
    container.innerHTML = '<div class="text-blue-400/30 italic text-xs">Could not load memories</div>';
  }
}

async function saveMemory() {
  const input = document.getElementById('memInput');
  const content = input.value.trim();
  if (!content) return;
  try {
    await fetch(`${API}/api/v1/memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, category: 'general' })
    });
    input.value = '';
    showToast('Memory saved', 'success');
    loadMemory();
  } catch { showToast('Failed to save memory', 'error'); }
}

// ---- SECURITY ----
async function loadSecurity() {
  const container = document.getElementById('securityEvents');
  try {
    const r = await fetch(`${API}/api/v1/security/events`);
    if (!r.ok) throw new Error();
    const events = await r.json();
    container.innerHTML = '';
    (Array.isArray(events) ? events : []).slice(0, 4).forEach(ev => {
      const item = document.createElement('div');
      item.className = 'sec-event';
      item.textContent = ev.message || ev.event || JSON.stringify(ev);
      container.appendChild(item);
    });
    if (container.children.length === 0) {
      container.innerHTML = '<div class="sec-event">No recent security events</div>';
    }
  } catch {
    container.innerHTML = '<div class="sec-event">API unreachable</div>';
  }
}

// ---- WORKFLOWS ----
async function loadWorkflows() {
  const container = document.getElementById('workflowList');
  try {
    const r = await fetch(`${API}/api/v1/workflows`);
    if (!r.ok) throw new Error();
    const flows = await r.json();
    container.innerHTML = '';
    (Array.isArray(flows) ? flows : []).slice(0, 8).forEach(wf => {
      const badge = document.createElement('button');
      badge.className = 'workflow-badge';
      badge.textContent = wf.name || wf.id;
      badge.onclick = () => runWorkflow(wf.id || wf.name);
      container.appendChild(badge);
    });
    if (container.children.length === 0) renderMockWorkflows(container);
  } catch { renderMockWorkflows(container); }
}

function renderMockWorkflows(container) {
  ['Morning Routine', 'Night Mode', 'Work Setup', 'Movie Night'].forEach(name => {
    const badge = document.createElement('button');
    badge.className = 'workflow-badge';
    badge.textContent = name;
    badge.onclick = () => showToast(`Running: ${name}`, 'info');
    container.appendChild(badge);
  });
}

async function runWorkflow(id) {
  try {
    await fetch(`${API}/api/v1/workflow/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workflow_id: id })
    });
    showToast(`Workflow "${id}" started`, 'success');
    sendCommand(`Run workflow: ${id}`);
  } catch { showToast('Workflow failed', 'error'); }
}

// ---- CANVAS BACKGROUND ----
function initBgCanvas() {
  const canvas = document.getElementById('bgCanvas');
  const ctx = canvas.getContext('2d');
  let particles = [];

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  for (let i = 0; i < 80; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.5,
      dx: (Math.random() - 0.5) * 0.3,
      dy: (Math.random() - 0.5) * 0.3,
      alpha: Math.random() * 0.4 + 0.1
    });
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,180,255,${p.alpha})`;
      ctx.fill();
      p.x += p.dx;
      p.y += p.dy;
      if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
      if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
    });
    requestAnimationFrame(draw);
  }
  draw();
}

// ---- TOAST ----
function showToast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.borderLeft = `3px solid ${type === 'error' ? '#ef4444' : type === 'success' ? '#00ff88' : '#00b4ff'}`;
  toast.innerHTML = `<span style="font-family:'Orbitron',sans-serif;font-size:0.65rem;color:rgba(0,180,255,0.7)">${type.toUpperCase()}</span> <span style="font-size:0.8rem;color:rgba(255,255,255,0.8)">${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ---- INIT ----
connectWS();
loadDevices();
loadMemory();
loadSecurity();
loadWorkflows();
initBgCanvas();
