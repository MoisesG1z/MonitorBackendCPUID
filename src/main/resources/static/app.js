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

// Basic OS Detection
function detectOS() {
    const userAgent = window.navigator.userAgent;
    let os = "Desconocido";
    if (userAgent.indexOf("Win") !== -1) os = "Windows";
    if (userAgent.indexOf("Mac") !== -1) os = "MacOS";
    if (userAgent.indexOf("Linux") !== -1) os = "Linux";
    
    document.getElementById('os-detected').innerText = os;
}

detectOS();

// Polling for data
let isConnected = false;
let pollingInterval;

function startPolling() {
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/data/${clientId}`);
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
