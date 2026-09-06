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

// Basic OS Detection & Script Generation
function detectOS() {
    const userAgent = window.navigator.userAgent;
    let os = "Desconocido";
    let isWindows = false;
    
    if (userAgent.indexOf("Win") !== -1) { os = "Windows"; isWindows = true; }
    if (userAgent.indexOf("Mac") !== -1) os = "MacOS";
    if (userAgent.indexOf("Linux") !== -1) os = "Linux";
    
    document.getElementById('os-detected').innerText = os;
    
    // Resolve the actual server URL. If API_BASE_URL is empty, use window.location.origin
    // But since agent needs a websocket URL, we convert http/https to ws/wss.
    // For the dynamic download, we assume the server is running on the API_BASE_URL.
    // NOTE: The python agent connects via WebSocket.
    let serverHttpUrl = API_BASE_URL || "http://localhost:8080";
    let serverWsUrl = serverHttpUrl.replace("http://", "ws://").replace("https://", "wss://");

    // We will download agent.py from this very same static site (Firebase)
    let agentDownloadUrl = window.location.origin + "/agent.py";
    
    const downloadContainer = document.getElementById('download-buttons');
    downloadContainer.innerHTML = '';

    if (isWindows || os === "Desconocido") {
        const batContent = `@echo off
echo =========================================
echo Analizador de Hardware - Instalacion
echo =========================================
echo.
echo 1. Instalando dependencias de Python (psutil, websocket-client, wmi)...
pip install psutil websocket-client wmi >nul 2>&1

echo 2. Descargando motor de analisis...
curl -s -o hw_agent.py "${agentDownloadUrl}"

echo 3. Ejecutando y conectando al dashboard...
echo Por favor, no cierres esta ventana mientras monitoreas.
python hw_agent.py ${clientId} ${serverWsUrl}
pause
`;
        const blob = new Blob([batContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'AnalizadorHardware.bat';
        a.className = 'btn btn-primary';
        a.innerHTML = 'Descargar para Windows (.bat)';
        a.style.marginRight = '10px';
        downloadContainer.appendChild(a);
    }
    
    if (!isWindows || os === "Desconocido") {
        const shContent = `#!/bin/bash
echo "========================================="
echo "Analizador de Hardware - Instalacion"
echo "========================================="
echo ""
echo "1. Instalando dependencias de Python..."
pip3 install psutil websocket-client >/dev/null 2>&1

echo "2. Descargando motor de analisis..."
curl -s -o hw_agent.py "${agentDownloadUrl}"

echo "3. Ejecutando y conectando al dashboard..."
echo "Por favor, no cierres esta ventana mientras monitoreas."
python3 hw_agent.py ${clientId} ${serverWsUrl}
`;
        const blob = new Blob([shContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'AnalizadorHardware.command';
        a.className = 'btn btn-primary';
        a.style.backgroundColor = '#4b5563'; // Darker for Mac/Linux distinction
        a.innerHTML = 'Descargar para Mac/Linux';
        downloadContainer.appendChild(a);
        
        if (!isWindows) {
            const terminalCmd = `curl -sL "${agentDownloadUrl}" -o hw_agent.py && pip3 install psutil websocket-client >/dev/null 2>&1 && python3 hw_agent.py ${clientId} ${serverWsUrl}`;
            
            const div = document.createElement('div');
            div.style.marginTop = '15px';
            div.style.background = 'rgba(0, 0, 0, 0.4)';
            div.style.padding = '12px';
            div.style.borderRadius = '8px';
            div.style.textAlign = 'left';
            div.innerHTML = `
                <p style="font-size: 13px; font-weight: 600; margin-bottom: 6px; color: #60a5fa;">💡 ¿macOS bloqueó el doble clic?</p>
                <p style="font-size: 12px; margin-bottom: 8px; opacity: 0.9;">Abre tu <strong>Terminal</strong> (Cmd + Espacio, escribe Terminal) y ejecuta cualquiera de estas dos opciones:</p>
                
                <p style="font-size: 12px; margin-bottom: 4px;"><strong>Opción A (Dar permiso al archivo descargado):</strong></p>
                <code style="display: block; background: #1e293b; padding: 6px 10px; border-radius: 4px; font-size: 11px; margin-bottom: 10px; color: #a7f3d0; word-break: break-all;">chmod +x ~/Downloads/AnalizadorHardware.command</code>
                
                <p style="font-size: 12px; margin-bottom: 4px;"><strong>Opción B (Ejecutar directo con 1 comando):</strong></p>
                <code style="display: block; background: #1e293b; padding: 6px 10px; border-radius: 4px; font-size: 11px; color: #a7f3d0; word-break: break-all;">${terminalCmd}</code>
            `;
            downloadContainer.appendChild(div);
        }
    }
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
    // OS Data
    const osHtml = `
        <p><strong>Sistema:</strong> ${data.os.system} ${data.os.release}</p>
        <p><strong>Arquitectura:</strong> ${data.os.architecture}</p>
        <p><strong>Hostname:</strong> ${data.os.hostname}</p>
    `;
    document.getElementById('os-data').innerHTML = osHtml;

    // CPU Data
    const cpuHtml = `
        <p><strong>Modelo:</strong> ${data.cpu.model || 'Desconocido'}</p>
        <p><strong>Núcleos:</strong> ${data.cpu.physical_cores} Físicos / ${data.cpu.logical_cores} Lógicos</p>
        <p><strong>Uso Actual:</strong> ${data.cpu.usage_percent}%</p>
        <p><strong>Frecuencia:</strong> ${data.cpu.freq_current} MHz</p>
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
            gpuHtml += `
                <p><strong>Dispositivo:</strong> ${g.name}</p>
                <p><strong>Carga:</strong> ${g.load}%</p>
                <p><strong>Memoria:</strong> ${g.memoryTotal}MB Total / ${g.memoryUsed}MB Usado</p>
                <hr style="border-color: rgba(255,255,255,0.1); margin: 5px 0;">
            `;
        });
    } else {
        gpuHtml = '<p>No se pudo detectar GPU o integrado.</p>';
    }
    document.getElementById('gpu-data').innerHTML = gpuHtml;

    // Storage Data
    let storageHtml = '';
    if (data.storage && data.storage.length > 0) {
        data.storage.forEach(d => {
            const diskHealth = d.health_percent !== undefined ? d.health_percent : 100;
            const hClass = getHealthClass(diskHealth);
            storageHtml += `
                <div style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <strong style="font-size: 16px;">${d.device} (${d.type})</strong>
                        <span class="health-indicator ${hClass}" style="margin:0; padding: 4px 8px; font-size:12px;">Salud: ${diskHealth}%</span>
                    </div>
                    <p style="margin:0; font-size:13px;"><strong>Modelo:</strong> ${d.model}</p>
                    <p style="margin:0; font-size:13px;"><strong>Tamaño:</strong> ${d.total_gb} GB (Usado: ${d.used_gb} GB)</p>
                    ${d.smart_status ? `<p style="margin:0; font-size:13px;"><strong>Estado SMART:</strong> ${d.smart_status}</p>` : ''}
                    ${d.issues ? `<p style="margin:2px 0 0 0; font-size:13px; color:#f87171;"><strong>Problemas:</strong> ${d.issues}</p>` : ''}
                </div>
            `;
        });
    } else {
        storageHtml = '<p>Buscando discos...</p>';
    }
    document.getElementById('storage-data').innerHTML = storageHtml;
}

// Start polling when page loads
startPolling();
