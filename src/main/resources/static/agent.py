import sys
import time
import json
import platform
import psutil
import websocket
import threading
import ssl
import subprocess
import re

def get_system_info():
    system = platform.system()
    brand = "Desconocido"
    model = "Desconocido"
    serial = "No disponible"
    os_name = f"{system} {platform.release()}"
    arch = platform.machine()

    if system == "Darwin":
        brand = "Apple Inc."
        try:
            model = subprocess.check_output(['sysctl', '-n', 'hw.model']).decode().strip()
        except:
            model = "Mac"
        try:
            out = subprocess.check_output(['ioreg', '-c', 'IOPlatformExpertDevice']).decode('utf-8')
            for line in out.splitlines():
                if 'IOPlatformSerialNumber' in line:
                    serial = line.split('=')[1].strip().strip('\"')
                    break
        except:
            serial = "No disponible"
        try:
            ver = subprocess.check_output(['sw_vers', '-productVersion']).decode().strip()
            major = int(ver.split('.')[0])
            names = {15: 'Sequoia', 14: 'Sonoma', 13: 'Ventura', 12: 'Monterey', 11: 'Big Sur'}
            os_name = f"macOS {names.get(major, '')} ({ver})".replace('  ', ' ')
            arch = "64-bit (Intel x86_64)" if platform.machine() == "x86_64" else "Apple Silicon (ARM64)"
        except:
            os_name = f"macOS {platform.release()}"

    elif system == "Windows":
        try:
            out_b = subprocess.check_output('wmic csproduct get vendor', shell=True).decode()
            lines = [l.strip() for l in out_b.splitlines() if l.strip()]
            if len(lines) > 1: brand = lines[1]
        except:
            brand = "PC Generico"
        try:
            out_m = subprocess.check_output('wmic csproduct get name', shell=True).decode()
            lines = [l.strip() for l in out_m.splitlines() if l.strip()]
            if len(lines) > 1: model = lines[1]
        except:
            model = "Windows PC"
        try:
            out_s = subprocess.check_output('wmic bios get serialnumber', shell=True).decode()
            lines = [l.strip() for l in out_s.splitlines() if l.strip()]
            if len(lines) > 1: serial = lines[1]
        except:
            serial = "No disponible"
        os_name = f"Windows {platform.release()}"
        arch = platform.architecture()[0]

    elif system == "Linux":
        try:
            with open('/sys/class/dmi/id/sys_vendor', 'r') as f: brand = f.read().strip()
        except: brand = "Linux PC"
        try:
            with open('/sys/class/dmi/id/product_name', 'r') as f: model = f.read().strip()
        except: model = "Linux PC"
        try:
            with open('/sys/class/dmi/id/product_serial', 'r') as f: serial = f.read().strip()
        except: serial = "No disponible"
        os_name = f"Linux {platform.release()}"

    return {
        "brand": brand,
        "model": model,
        "serial": serial,
        "os_name": os_name,
        "architecture": arch
    }

def get_cpu_generation(brand_string):
    if 'Apple' in brand_string or 'M1' in brand_string or 'M2' in brand_string or 'M3' in brand_string or 'M4' in brand_string:
        match = re.search(r'M[1-4](?:\s+(?:Pro|Max|Ultra))?', brand_string)
        return f"Apple Silicon ({match.group(0)})" if match else "Apple Silicon"
    
    intel_match = re.search(r'i[3579]-(\d{3,5})', brand_string, re.IGNORECASE)
    if intel_match:
        digits = intel_match.group(1)
        gen = digits[0] if len(digits) == 4 else (digits[:2] if len(digits) == 5 else None)
        if gen:
            return f"{gen}ª Generación"
            
    ryzen_match = re.search(r'Ryzen\s+[3579]\s+(\d{4})', brand_string, re.IGNORECASE)
    if ryzen_match:
        return f"Serie {ryzen_match.group(1)[0]}000"
        
    return "Generación Estándar"

def get_cpu_info():
    try:
        freq = psutil.cpu_freq()
        freq_ghz = round(freq.current / 1000.0, 2) if freq and freq.current > 0 else 0
        
        brand_string = platform.processor()
        if platform.system() == "Darwin":
            try:
                brand_string = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
            except:
                pass
        elif platform.system() == "Windows":
            try:
                out = subprocess.check_output('wmic cpu get name', shell=True).decode()
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                if len(lines) > 1: brand_string = lines[1]
            except:
                pass

        if not brand_string or brand_string == "i386":
            brand_string = "Procesador de Sistema"

        gen = get_cpu_generation(brand_string)

        return {
            "model": brand_string,
            "generation": gen,
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "usage_percent": psutil.cpu_percent(interval=1),
            "freq_ghz": freq_ghz if freq_ghz > 0 else 1.60
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
            if 'loop' in partition.device or 'snap' in partition.mountpoint:
                continue
                
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                total_gb = round(usage.total / (1024 ** 3), 2)
                used_gb = round(usage.used / (1024 ** 3), 2)
                percent = usage.percent
                
                health = 100
                issues = ""
                if percent > 95:
                    health = 30
                    issues = "Poco espacio (Crítico)"
                elif percent > 85:
                    health = 60
                    issues = "Poco espacio (Advertencia)"
                
                smart_status = "OK (Simulado/Basado en uso)" if health > 50 else "Advertencia"

                storage_list.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "type": partition.fstype,
                    "model": "Disco/Partición Local",
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "usage_percent": percent,
                    "health_percent": health,
                    "smart_status": smart_status,
                    "issues": issues
                })
            except PermissionError:
                continue
    except Exception as e:
        print(f"Error reading storage: {e}")
        
    return storage_list

def get_gpu_info():
    gpus = []
    try:
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
        gpus.append({
            "name": "GPU Genérica / Integrada",
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
                "system_info": get_system_info(),
                "os": get_system_info(), # Backward compatibility
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
    
    while True:
        try:
            print(f"Conectando a {ws_url}...")
            ws = websocket.WebSocketApp(ws_url,
                                      on_open=on_open,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close)

            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        except Exception as e:
            print(f"Error de conexión: {e}")
            
        print("Reintentando conexión en 3 segundos...")
        time.sleep(3)
