import sys
import time
import json
import platform
import psutil
import websocket
import threading
import ssl


def get_os_info():
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node()
    }

def get_cpu_info():
    try:
        freq = psutil.cpu_freq()
        return {
            "model": platform.processor(),
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "usage_percent": psutil.cpu_percent(interval=1),
            "freq_current": round(freq.current, 2) if freq else 0
        }
    except Exception as e:
        return {"error": str(e)}

def get_ram_info():
    try:
        svmem = psutil.virtual_memory()
        total_gb = round(svmem.total / (1024 ** 3), 2)
        used_gb = round(svmem.used / (1024 ** 3), 2)
        available_gb = round(svmem.available / (1024 ** 3), 2)
        usage_percent = svmem.percent
        
        # Simple health calculation based on usage
        health_percent = 100
        if usage_percent > 95:
            health_percent = 30
        elif usage_percent > 85:
            health_percent = 60
        elif usage_percent > 70:
            health_percent = 80
            
        return {
            "total_gb": total_gb,
            "used_gb": used_gb,
            "available_gb": available_gb,
            "usage_percent": usage_percent,
            "health_percent": health_percent
        }
    except Exception as e:
        return {"error": str(e)}

def get_storage_info():
    storage_list = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for partition in partitions:
            # Skip loop devices and similar on linux/mac
            if 'loop' in partition.device or 'snap' in partition.mountpoint:
                continue
                
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                total_gb = round(usage.total / (1024 ** 3), 2)
                used_gb = round(usage.used / (1024 ** 3), 2)
                percent = usage.percent
                
                # Basic health heuristic based on capacity
                health = 100
                issues = ""
                if percent > 95:
                    health = 30
                    issues = "Poco espacio (Crítico)"
                elif percent > 85:
                    health = 60
                    issues = "Poco espacio (Advertencia)"
                
                # In a real deep agent, we would run smartctl or wmi to get SMART data here.
                # Since this needs admin rights and specific OS commands, we simulate it or use basic heuristics for now.
                smart_status = "OK (Simulado/Basado en uso)" if health > 50 else "Advertencia"

                storage_list.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "type": partition.fstype,
                    "model": "Disco/Partición Local", # Detailed model requires WMI/smartctl
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "usage_percent": percent,
                    "health_percent": health,
                    "smart_status": smart_status,
                    "issues": issues
                })
            except PermissionError:
                # Can't read this disk
                continue
    except Exception as e:
        print(f"Error reading storage: {e}")
        
    return storage_list

def get_gpu_info():
    # To get GPU info in Python without external C libraries, we usually need specific packages.
    # We will simulate or provide basic placeholders if GPUtil is not installed.
    gpus = []
    try:
        # Try to use GPUtil if available (mostly works for NVIDIA)
        import GPUtil
        gpu_list = GPUtil.getGPUs()
        for gpu in gpu_list:
            gpus.append({
                "name": gpu.name,
                "load": round(gpu.load * 100, 2),
                "memoryTotal": gpu.memoryTotal,
                "memoryUsed": gpu.memoryUsed
            })
    except ImportError:
        # Fallback or generic message
        gpus.append({
            "name": "GPU Genérica/Integrada (Instalar GPUtil para NVIDIA)",
            "load": 0,
            "memoryTotal": 0,
            "memoryUsed": 0
        })
    except Exception as e:
         pass
    return gpus

def send_data(ws):
    while True:
        try:
            data = {
                "os": get_os_info(),
                "cpu": get_cpu_info(),
                "ram": get_ram_info(),
                "storage": get_storage_info(),
                "gpu": get_gpu_info(),
                "timestamp": time.time()
            }
            ws.send(json.dumps(data))
            time.sleep(2)
        except Exception as e:
            print(f"Error sending data: {e}")
            break

def on_message(ws, message):
    pass

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Conexión cerrada.")

def on_open(ws):
    print("Conectado al servidor. Enviando datos...")
    # Start thread to send data continuously
    t = threading.Thread(target=send_data, args=(ws,))
    t.start()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python agent.py <CLIENT_ID> [SERVER_URL]")
        sys.exit(1)
        
    client_id = sys.argv[1]
    server_url = "ws://localhost:8080"
    if len(sys.argv) >= 3:
        server_url = sys.argv[2]
        
    ws_url = f"{server_url}/ws/agent/{client_id}"
    
    print(f"Iniciando agente para cliente {client_id}...")
    print(f"Conectando a {ws_url}...")
    
    ws = websocket.WebSocketApp(ws_url,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)

    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
