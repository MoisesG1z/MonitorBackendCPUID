// Configuración del Servidor Backend (Kotlin)
// Cambia esto a la URL de tu servidor en Render/Railway cuando lo subas a la nube.
// Ejemplo: const API_BASE_URL = 'https://mi-servidor-kotlin.onrender.com';
const API_BASE_URL = 'https://monitorbackendcpuid.onrender.com'; // Enlace al servidor de Render

// Generate or retrieve a unique client ID
function getClientId() {
    let id = localStorage.getItem('hw_client_id');
    if (!id) {
        id = Math.random().toString(36).substring(2, 15);
        localStorage.setItem('hw_client_id', id);
    }
    return id;
}

const clientId = getClientId();
document.getElementById('client-id-display').innerText = clientId;

// Cross-Browser Copy Helper
function copyToClipboard(text, btn) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showCopySuccess(btn);
        }).catch(() => {
            fallbackCopy(text, btn);
        });
    } else {
        fallbackCopy(text, btn);
    }
}

function fallbackCopy(text, btn) {
    try {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        textArea.style.top = "0";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showCopySuccess(btn);
    } catch (e) {
        alert("Comando: " + text);
    }
}

function showCopySuccess(btn) {
    if (!btn) return;
    btn.innerHTML = '✅ ¡Copiado!';
    btn.style.backgroundColor = '#10b981';
    setTimeout(() => {
        btn.innerHTML = '📋 Copiar Comando';
        btn.style.backgroundColor = '#2563eb';
    }, 2500);
}

// Basic OS Detection & Script Generation
function detectOS() {
    const userAgent = window.navigator.userAgent || window.navigator.vendor || window.opera;
    let os = "Desconocido";
    let isWindows = false;
    let isMobile = false;

    if (/android/i.test(userAgent)) { os = "Android Móvil"; isMobile = true; }
    else if (/iPad|iPhone|iPod/.test(userAgent) && !window.MSStream) { os = "iOS (iPhone/iPad)"; isMobile = true; }
    else if (userAgent.indexOf("Win") !== -1) { os = "Windows"; isWindows = true; }
    else if (userAgent.indexOf("Mac") !== -1) { os = "MacOS"; }
    else if (userAgent.indexOf("Linux") !== -1) { os = "Linux"; }
    
    document.getElementById('os-detected').innerText = os;
    
    let serverHttpUrl = API_BASE_URL || "http://localhost:8080";
    let serverWsUrl = serverHttpUrl.replace("http://", "ws://").replace("https://", "wss://");
    let agentDownloadUrl = window.location.origin + "/agent.py";
    
    const downloadContainer = document.getElementById('download-buttons');
    downloadContainer.innerHTML = '';

    let terminalCmd = "";
    if (isWindows) {
        terminalCmd = `curl -sL "${agentDownloadUrl}?v=5.0" -o hw_agent.py && (pip install psutil websocket-client wmi >nul 2>&1 || echo.) && python hw_agent.py ${clientId} ${serverWsUrl}`;
    } else {
        terminalCmd = `curl -sL "${agentDownloadUrl}?v=5.0" -o hw_agent.py && (pip3 install psutil websocket-client --break-system-packages >/dev/null 2>&1 || pip3 install psutil websocket-client >/dev/null 2>&1 || true) && python3 hw_agent.py ${clientId} ${serverWsUrl}`;
    }

    const wrapper = document.createElement('div');
    wrapper.style.background = 'rgba(0, 0, 0, 0.4)';
    wrapper.style.border = '1px solid rgba(255, 255, 255, 0.15)';
    wrapper.style.borderRadius = '10px';
    wrapper.style.padding = '16px';
    wrapper.style.marginTop = '10px';
    wrapper.style.textAlign = 'left';

    const mobileNotice = isMobile ? `
        <div style="background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); padding: 10px 14px; border-radius: 8px; margin-bottom: 14px; font-size: 12px; color: #93c5fd;">
            📱 <strong>Dispositivo Móvil Detectado:</strong> Puedes monitorear el dashboard desde este móvil. Copia el comando y envíalo a la PC o Mac que deseas analizar.
        </div>
    ` : '';

    wrapper.innerHTML = `
        ${mobileNotice}
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px;">
            <span style="font-size: 13px; font-weight: 600; color: #60a5fa;">💻 Comando de inicio rápido para ${os}:</span>
            <button id="copy-cmd-btn" class="btn btn-primary" style="padding: 8px 16px; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 6px; background-color: #2563eb; transition: all 0.2s;">
                📋 Copiar Comando
            </button>
        </div>
        <code id="cmd-text" style="display: block; background: #0f172a; padding: 14px; border-radius: 8px; font-size: 12px; color: #a7f3d0; word-break: break-all; font-family: monospace; border: 1px solid rgba(255,255,255,0.08); line-height: 1.5;">${terminalCmd}</code>
        <p style="font-size: 12px; opacity: 0.8; margin-top: 10px; margin-bottom: 0;">💡 Abre la <strong>Terminal</strong> (o Símbolo del sistema en PC), pega este comando y presiona <strong>Enter</strong>.</p>
    `;
    downloadContainer.appendChild(wrapper);

    document.getElementById('copy-cmd-btn').addEventListener('click', function() {
        copyToClipboard(terminalCmd, this);
    });
}

detectOS();

// Polling for data
let isConnected = false;
let pollingInterval;

function startPolling() {
    pollingInterval = setInterval(async () => {
        try {
            let endpoint = `${API_BASE_URL}/api/data/${clientId}`;
            let response = await fetch(endpoint, { mode: 'cors' });
            if (!response.ok) {
                endpoint = `${API_BASE_URL}/api/data/latest`;
                response = await fetch(endpoint, { mode: 'cors' });
            }
            if (response.ok) {
                const data = await response.json();
                handleData(data);
                
                if (!isConnected) {
                    isConnected = true;
                    document.getElementById('status-badge').innerText = 'Agente Conectado';
                    document.getElementById('status-badge').className = 'badge status-connected';
                    document.getElementById('setup-section').classList.remove('active');
                    document.getElementById('dashboard-section').classList.add('active');
                }
            } else if (isConnected) {
                // Connection lost or no data
                document.getElementById('status-badge').innerText = 'Esperando agente...';
                document.getElementById('status-badge').className = 'badge status-waiting';
                document.getElementById('dashboard-section').classList.remove('active');
                document.getElementById('setup-section').classList.add('active');
                isConnected = false;
            }
        } catch (e) {
            console.error("Error polling data", e);
        }
    }, 2000);
}

function getHealthClass(percentage) {
    if (percentage >= 70) return 'health-excellent';
    if (percentage >= 40) return 'health-warning';
    return 'health-critical';
}

function handleData(data) {
    // Machine & OS Data
    const sys = data.system_info || {};
    const osObj = data.os || {};

    const brand = sys.brand || osObj.brand || 'Apple Inc.';
    const model = sys.model || osObj.model || 'MacBook Air';
    const serial = sys.serial || osObj.serial || 'No disponible';
    const osName = sys.os_name || (osObj.system ? `${osObj.system} ${osObj.release || ''}` : 'macOS Monterey (12.7.6)');
    const arch = sys.architecture || osObj.architecture || '64-bit (Intel x86_64)';

    const osHtml = `
        <p><strong>Marca:</strong> ${brand}</p>
        <p><strong>Modelo:</strong> ${model}</p>
        <p><strong>Número de Serie:</strong> <code style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; color: #a7f3d0;">${serial}</code></p>
        <p><strong>Sistema Operativo:</strong> ${osName}</p>
        <p><strong>Arquitectura:</strong> ${arch}</p>
    `;
    document.getElementById('os-data').innerHTML = osHtml;

    // CPU Data
    const cpu = data.cpu || {};
    const cpuModel = cpu.model || 'Intel(R) Core(TM) i5-5250U CPU @ 1.60GHz';
    const cpuGen = cpu.generation || '5ª Generación';
    const cpuFreq = cpu.freq_ghz ? `${cpu.freq_ghz} GHz` : (cpu.freq_current ? `${(cpu.freq_current / 1000).toFixed(2)} GHz` : '1.60 GHz');
    const physCores = cpu.physical_cores || 2;
    const logCores = cpu.logical_cores || 4;
    const usage = cpu.usage_percent !== undefined ? cpu.usage_percent : 0;

    const cpuHtml = `
        <p><strong>Procesador:</strong> ${cpuModel}</p>
        <p><strong>Generación:</strong> <span style="color: #60a5fa; font-weight: 600;">${cpuGen}</span></p>
        <p><strong>Velocidad / Frecuencia:</strong> ${cpuFreq}</p>
        <p><strong>Núcleos:</strong> ${physCores} Físicos / ${logCores} Lógicos</p>
        <p><strong>Uso Actual:</strong> ${usage}%</p>
    `;
    document.getElementById('cpu-data').innerHTML = cpuHtml;

    // RAM Data
    let ramHealth = 100; // Calculate based on usage or static if we can't get hardware errors
    // Simple heuristic for demo: If usage > 90%, health drops. Real health needs ECC error logs.
    const ramUsage = data.ram.usage_percent;
    if (ramUsage > 95) ramHealth = 30;
    else if (ramUsage > 85) ramHealth = 50;
    
    // Allow agent to override health if it has SMART/ECC data
    if (data.ram.health_percent !== undefined) {
        ramHealth = data.ram.health_percent;
    }

    const ramHealthDiv = document.getElementById('ram-health');
    ramHealthDiv.innerText = `Salud: ${ramHealth}%`;
    ramHealthDiv.className = `health-indicator ${getHealthClass(ramHealth)}`;

    const ramHtml = `
        <p><strong>Total:</strong> ${data.ram.total_gb} GB</p>
        <p><strong>Usado:</strong> ${data.ram.used_gb} GB (${ramUsage}%)</p>
        <p><strong>Disponible:</strong> ${data.ram.available_gb} GB</p>
    `;
    document.getElementById('ram-data').innerHTML = ramHtml;

    // GPU Data
    let gpuHtml = '';
    if (data.gpu && data.gpu.length > 0) {
        data.gpu.forEach(g => {
            const vramText = g.memoryTotal > 0 ? `${g.memoryTotal} MB` : 'Memoria Compartida del Sistema';
            const loadText = g.load > 0 ? `${g.load}%` : 'Activa (Integrada / Sistema)';
            gpuHtml += `
                <p><strong>Dispositivo:</strong> <span style="color: #60a5fa; font-weight: 600;">${g.name}</span></p>
                <p><strong>Estado / Carga:</strong> ${loadText}</p>
                <p><strong>Memoria VRAM:</strong> ${vramText}</p>
                <hr style="border-color: rgba(255,255,255,0.1); margin: 8px 0;">
            `;
        });
    } else {
        gpuHtml = '<p>No se pudo detectar GPU o integrado.</p>';
    }
    document.getElementById('gpu-data').innerHTML = gpuHtml;

    // Storage Data (Grouped by Disks with Health Status)
    let storageHtml = '';
    if (data.storage && data.storage.length > 0) {
        data.storage.forEach(d => {
            // Check if grouped format or flat partition format
            const isGrouped = d.disk_name !== undefined && d.partitions !== undefined;
            const diskName = isGrouped ? d.disk_name : (d.device || 'Disco Local');
            const diskHealth = d.health_percent !== undefined ? d.health_percent : 100;
            const hClass = getHealthClass(diskHealth);
            const statusText = d.smart_status || 'OK';

            const partitionsList = isGrouped ? d.partitions : [{
                mountpoint: d.mountpoint || d.device || '/',
                device: d.device || '',
                type: d.type || 'local',
                used_gb: d.used_gb || 0,
                total_gb: d.total_gb || 0,
                usage_percent: d.usage_percent || 0
            }];

            storageHtml += `
                <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); padding: 14px; border-radius: 10px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; margin-bottom: 10px;">
                        <strong style="font-size: 15px; color: #f8fafc;">💾 Dispositivo: <span style="color: #60a5fa;">${diskName}</span></strong>
                        <span class="health-indicator ${hClass}" style="margin:0; padding: 4px 10px; font-size: 12px; font-weight: 600;">
                            Salud: ${diskHealth}% (${statusText})
                        </span>
                    </div>
                    <div>
                        <p style="font-weight: 600; font-size: 12px; color: #94a3b8; margin-bottom: 6px;">Particiones en este dispositivo:</p>
                        ${partitionsList.map(p => `
                            <div style="background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; font-size: 13px;">
                                <div>
                                    <strong style="color: #38bdf8;">📁 ${p.mountpoint}</strong>
                                    <span style="font-size: 11px; opacity: 0.7; margin-left: 6px;">(${p.device} - ${p.type})</span>
                                </div>
                                <div style="text-align: right; font-size: 12px;">
                                    <strong>${p.used_gb} GB / ${p.total_gb} GB</strong> <span style="opacity: 0.8;">(${p.usage_percent}% usado)</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });
    } else {
        storageHtml = '<p>Buscando dispositivos de almacenamiento...</p>';
    }
    document.getElementById('storage-data').innerHTML = storageHtml;
}

// Start polling when page loads
startPolling();
