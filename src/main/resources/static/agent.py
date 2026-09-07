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
import os

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
            if len(lines) > 1 and lines[1] and lines[1] not in ['To be filled by O.E.M.', 'System manufacturer']:
                brand = lines[1]
        except:
            brand = "PC Generico"

        try:
            out_m = subprocess.check_output('wmic csproduct get name', shell=True).decode()
            lines = [l.strip() for l in out_m.splitlines() if l.strip()]
            if len(lines) > 1 and lines[1] and lines[1] not in ['To be filled by O.E.M.', 'System Product Name']:
                model = lines[1]
        except:
            model = "Windows PC"

        # Windows Serial Number Brute Force (BIOS -> BaseBoard -> CSProduct -> OS Serial)
        try:
            out_s = subprocess.check_output('wmic bios get serialnumber', shell=True).decode()
            lines = [l.strip() for l in out_s.splitlines() if l.strip()]
            if len(lines) > 1 and lines[1] and lines[1] not in ['To be filled by O.E.M.', 'Default string', '0', '00000000', 'None']:
                serial = lines[1]
        except: pass

        if serial == "No disponible":
            try:
                out_b = subprocess.check_output('wmic baseboard get serialnumber', shell=True).decode()
                lines = [l.strip() for l in out_b.splitlines() if l.strip()]
                if len(lines) > 1 and lines[1] and lines[1] not in ['To be filled by O.E.M.', 'Default string', '0', '00000000', 'None']:
                    serial = lines[1]
            except: pass

        if serial == "No disponible":
            try:
                out_c = subprocess.check_output('wmic csproduct get identifyingnumber', shell=True).decode()
                lines = [l.strip() for l in out_c.splitlines() if l.strip()]
                if len(lines) > 1 and lines[1] and lines[1] not in ['To be filled by O.E.M.', 'Default string', '0', '00000000', 'None']:
                    serial = lines[1]
            except: pass

        if serial == "No disponible":
            try:
                out_os = subprocess.check_output('wmic os get serialnumber', shell=True).decode()
                lines = [l.strip() for l in out_os.splitlines() if l.strip()]
                if len(lines) > 1 and lines[1]:
                    serial = f"WIN-{lines[1]}"
            except: pass

        os_name = f"Windows {platform.release()}"
        arch = platform.architecture()[0]

    elif system == "Linux":
        # 1. Brand Brute Force
        for path in ['/sys/class/dmi/id/sys_vendor', '/sys/class/dmi/id/board_vendor']:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        val = f.read().strip()
                        if val and val not in ["To Be Filled By O.E.M.", "System manufacturer"]:
                            brand = val
                            break
                except: pass
        if brand == "Desconocido":
            try:
                out = subprocess.check_output("hostnamectl 2>/dev/null | grep 'Hardware Vendor:'", shell=True).decode()
                if out: brand = out.split(':', 1)[1].strip()
            except: pass

        # 2. Model Brute Force
        for path in ['/sys/class/dmi/id/product_name', '/sys/class/dmi/id/board_name', '/sys/class/dmi/id/product_family']:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        val = f.read().strip()
                        if val and val not in ["To Be Filled By O.E.M.", "System Product Name"]:
                            model = val
                            break
                except: pass
        if model == "Desconocido":
            try:
                out = subprocess.check_output("hostnamectl 2>/dev/null | grep 'Hardware Model:'", shell=True).decode()
                if out: model = out.split(':', 1)[1].strip()
            except: pass

        # 3. Serial Number Brute Force
        for path in [
            '/sys/class/dmi/id/product_serial',
            '/sys/class/dmi/id/chassis_serial',
            '/sys/class/dmi/id/board_serial',
            '/sys/devices/virtual/dmi/id/product_serial',
            '/sys/firmware/devicetree/base/serial-number'
        ]:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        val = f.read().strip()
                        if val and val not in ["To Be Filled By O.E.M.", "None", "00000000", "Default string", "System Serial Number"]:
                            serial = val
                            break
                except: pass

        if serial == "No disponible":
            try:
                out = subprocess.check_output("sudo -n dmidecode -s system-serial-number 2>/dev/null || dmidecode -s system-serial-number 2>/dev/null", shell=True).decode().strip()
                if out and out not in ["To Be Filled By O.E.M.", "None", "00000000", "Default string"]:
                    serial = out
            except: pass

        if serial == "No disponible":
            try:
                out = subprocess.check_output("udevadm info --query=property --name=/dev/sda 2>/dev/null | grep ID_SERIAL_SHORT=", shell=True).decode().strip()
                if out:
                    serial = out.split('=')[1].strip()
            except: pass

        if serial == "No disponible":
            try:
                with open('/etc/machine-id', 'r') as f:
                    mid = f.read().strip()
                    if mid:
                        serial = f"ID-{mid[:12].upper()}"
            except: pass

        os_name = f"Linux {platform.release()}"
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        os_name = line.split('=', 1)[1].strip().strip('"')
                        break
        except: pass

    return {
        "brand": brand,
        "model": model,
        "serial": serial,
        "os_name": os_name,
        "architecture": arch
    }

def get_cpu_generation(brand_string):
    if not brand_string:
        return ""
    if 'Apple' in brand_string or 'M1' in brand_string or 'M2' in brand_string or 'M3' in brand_string or 'M4' in brand_string:
        match = re.search(r'M[1-4](?:\s+(?:Pro|Max|Ultra))?', brand_string)
        return f"Apple Silicon ({match.group(0)})" if match else "Apple Silicon"
    
    intel_match = re.search(r'i[3579]-(\d{3,5})', brand_string, re.IGNORECASE)
    if intel_match:
        digits = intel_match.group(1)
        gen = digits[0] if len(digits) == 4 else (digits[:2] if len(digits) == 5 else None)
        if gen:
            return f"{gen}ª Generación Intel"
            
    ryzen_match = re.search(r'Ryzen\s+[3579]\s+(\d{4})', brand_string, re.IGNORECASE)
    if ryzen_match:
        return f"AMD Ryzen Serie {ryzen_match.group(1)[0]}000"
        
    return ""

def get_cpu_info():
    try:
        freq = psutil.cpu_freq()
        freq_ghz = round(freq.current / 1000.0, 2) if freq and freq.current > 0 else 0
        
        brand_string = ""
        system = platform.system()

        if system == "Linux":
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            brand_string = line.split(':', 1)[1].strip()
                            break
            except: pass
            
            if not brand_string:
                try:
                    out = subprocess.check_output("lscpu 2>/dev/null | grep 'Model name:'", shell=True).decode()
                    if out:
                        brand_string = out.split(':', 1)[1].strip()
                except: pass

        elif system == "Darwin":
            try:
                brand_string = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
            except: pass

        elif system == "Windows":
            try:
                out = subprocess.check_output('wmic cpu get name', shell=True).decode()
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                if len(lines) > 1: brand_string = lines[1]
            except: pass

        if not brand_string or brand_string.lower() in ["x86_64", "i386", "arm64", "unknown"]:
            brand_string = platform.processor() or "Procesador Intel / AMD"

        brand_string = re.sub(r'\s+', ' ', brand_string).strip()
        gen = get_cpu_generation(brand_string)

        return {
            "model": brand_string,
            "generation": gen if gen != "Generación Estándar" else "",
            "physical_cores": psutil.cpu_count(logical=False) or 1,
            "logical_cores": psutil.cpu_count(logical=True) or 1,
            "usage_percent": psutil.cpu_percent(interval=1),
            "freq_ghz": freq_ghz if freq_ghz > 0 else 2.0
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
    system = platform.system()
    disks_dict = {}
    drive_to_disk = {}

    # Step 1: Detect physical disks on Linux via lsblk
    if system == "Linux":
        try:
            out = subprocess.check_output("lsblk -b -P -o NAME,MODEL,VENDOR,SIZE,TYPE,MOUNTPOINT,FSTYPE 2>/dev/null", shell=True).decode()
            for line in out.splitlines():
                items = dict(re.findall(r'([A-Z_]+)="([^"]*)"', line))
                dev_name = items.get('NAME', '')
                dev_type = items.get('TYPE', '')
                vendor = items.get('VENDOR', '').strip()
                model = items.get('MODEL', '').strip()
                size_bytes = int(items.get('SIZE', 0)) if items.get('SIZE', '').isdigit() else 0
                size_gb = round(size_bytes / (1024**3), 2) if size_bytes > 0 else 0
                
                dev_path = f"/dev/{dev_name}"

                if dev_type == "disk":
                    full_model = f"{vendor} {model}".strip()
                    if not full_model:
                        try:
                            with open(f"/sys/block/{dev_name}/device/model", 'r') as f:
                                full_model = f.read().strip()
                        except: pass
                    
                    if not full_model:
                        full_model = f"Disco Físico ({dev_name})"

                    disk_title = f"{full_model} ({size_gb} GB)" if size_gb > 0 else full_model

                    disks_dict[dev_path] = {
                        "disk_name": disk_title,
                        "device": dev_path,
                        "health_percent": 100,
                        "smart_status": "OK (S.M.A.R.T)",
                        "partitions": []
                    }
        except Exception as e:
            print(f"Error in lsblk execution: {e}")

    # Step 1b: Detect physical disks on Windows via WMIC + LogicalDiskToPartition
    elif system == "Windows":
        try:
            # Query Win32_DiskDrive
            out_disk = subprocess.check_output('wmic diskdrive get DeviceID,Model,Size,Caption /format:csv', shell=True).decode()
            for line in out_disk.splitlines():
                line = line.strip()
                if not line or line.startswith('Node'): continue
                parts = line.split(',')
                # Format: Node, Caption, DeviceID, Model, Size
                if len(parts) >= 5:
                    caption = parts[1].strip()
                    dev_id = parts[2].strip()
                    model = parts[3].strip() or caption
                    try:
                        size_bytes = int(parts[4].strip())
                        size_gb = round(size_bytes / (1024**3), 2)
                    except: size_gb = 0

                    if dev_id and model:
                        full_name = f"{model} ({size_gb} GB)" if size_gb > 0 else model
                        disks_dict[dev_id] = {
                            "disk_name": full_name,
                            "device": dev_id,
                            "health_percent": 100,
                            "smart_status": "OK (S.M.A.R.T)",
                            "partitions": []
                        }

            # Query LogicalDiskToPartition to map drive letters (C:, G:) to PHYSICALDRIVE
            out_map = subprocess.check_output('wmic path Win32_LogicalDiskToPartition get Antecedent,Dependent /format:csv', shell=True).decode()
            for line in out_map.splitlines():
                if not line or line.startswith('Node'): continue
                parts = line.split(',')
                if len(parts) >= 3:
                    antecedent = parts[1]
                    dependent = parts[2]
                    disk_match = re.search(r'Disk #(\d+)', antecedent)
                    drive_match = re.search(r'([A-Z]:)', dependent, re.IGNORECASE)
                    if disk_match and drive_match:
                        disk_num = disk_match.group(1)
                        drive_letter = drive_match.group(1).upper()
                        phys_dev = f"\\\\.\\PHYSICALDRIVE{disk_num}"
                        drive_to_disk[drive_letter] = phys_dev
        except Exception as e:
            print(f"Windows physical disk detection error: {e}")

    # Step 2: Extract mounted partitions with psutil & map to physical disk
    partitions = psutil.disk_partitions(all=False)
    for p in partitions:
        if 'loop' in p.device or 'snap' in p.mountpoint:
            continue
        if system == "Darwin" and any(x in p.mountpoint for x in ['Preboot', 'Update', 'VM']):
            continue

        try:
            usage = psutil.disk_usage(p.mountpoint)
            total_gb = round(usage.total / (1024 ** 3), 2)
            used_gb = round(usage.used / (1024 ** 3), 2)
            percent = usage.percent

            part_info = {
                "mountpoint": p.mountpoint,
                "device": p.device,
                "type": p.fstype,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "usage_percent": percent
            }

            # Find which physical disk container this partition belongs to
            target_disk_key = None

            if system == "Windows":
                # Drive letter matching (e.g. C: -> \\.\PHYSICALDRIVE0)
                drive_letter = p.mountpoint[:2].upper() if len(p.mountpoint) >= 2 else ""
                if drive_letter in drive_to_disk and drive_to_disk[drive_letter] in disks_dict:
                    target_disk_key = drive_to_disk[drive_letter]
            else:
                # Linux / Darwin matching
                parent_dev = re.sub(r'p?\d+$', '', p.device)
                if p.device in disks_dict:
                    target_disk_key = p.device
                elif parent_dev in disks_dict:
                    target_disk_key = parent_dev
                elif p.device.startswith('/dev/mapper/') or 'mapper' in p.device:
                    target_disk_key = next(iter(disks_dict.keys()), None) if disks_dict else None

            # Fallback if no pre-registered physical disk matched
            if not target_disk_key:
                disk_label = p.mountpoint
                if system == "Windows":
                    disk_label = f"Disco Físico ({p.mountpoint})"
                elif system == "Linux":
                    short_dev = os.path.basename(re.sub(r'p?\d+$', '', p.device))
                    model_path = f"/sys/block/{short_dev}/device/model"
                    vendor_path = f"/sys/block/{short_dev}/device/vendor"
                    model_str = ""
                    if os.path.exists(model_path):
                        try:
                            with open(model_path, 'r') as f: model_str = f.read().strip()
                        except: pass
                    if os.path.exists(vendor_path):
                        try:
                            with open(vendor_path, 'r') as f: model_str = f"{f.read().strip()} {model_str}".strip()
                        except: pass
                    if model_str:
                        disk_label = f"{model_str} ({short_dev})"
                    else:
                        disk_label = f"Dispositivo de Almacenamiento ({p.device})"
                elif system == "Darwin":
                    disk_label = "Disco Almacenamiento Principal (SSD)"

                target_disk_key = p.mountpoint
                if target_disk_key not in disks_dict:
                    disks_dict[target_disk_key] = {
                        "disk_name": disk_label,
                        "device": target_disk_key,
                        "health_percent": 100,
                        "smart_status": "OK (S.M.A.R.T)",
                        "partitions": []
                    }

            disks_dict[target_disk_key]["partitions"].append(part_info)

            if percent > 95:
                disks_dict[target_disk_key]["health_percent"] = 30
                disks_dict[target_disk_key]["smart_status"] = "Crítico (Espacio)"
            elif percent > 85 and disks_dict[target_disk_key]["health_percent"] > 60:
                disks_dict[target_disk_key]["health_percent"] = 60
                disks_dict[target_disk_key]["smart_status"] = "Advertencia (Espacio)"

        except PermissionError:
            continue
        except Exception as e:
            print(f"Error reading partition {p.device}: {e}")

    final_disks = [d for d in disks_dict.values() if len(d["partitions"]) > 0]
    return final_disks

def get_gpu_info():
    gpus = []
    system = platform.system()

    # 1. Try GPUtil (NVIDIA)
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
    except: pass

    # 2. Linux Brute Force (lspci / lshw)
    if not gpus and system == "Linux":
        try:
            out = subprocess.check_output("lspci -nn 2>/dev/null | grep -iE 'vga|3d|display'", shell=True).decode()
            for line in out.splitlines():
                if ':' in line:
                    parts = line.split(':', 2)
                    card_name = parts[-1].strip() if len(parts) >= 3 else line
                    card_name = re.sub(r'\[[0-9a-fA-F]{4}:[0-9a-fA-F]{4}\]', '', card_name).strip()
                    card_name = re.sub(r'\(rev \d+\)', '', card_name).strip()
                    if card_name:
                        gpus.append({
                            "name": card_name,
                            "load": 0,
                            "memoryTotal": 0,
                            "memoryUsed": 0
                        })
        except: pass

        if not gpus:
            try:
                out = subprocess.check_output("lshw -C display 2>/dev/null | grep 'product:'", shell=True).decode()
                for line in out.splitlines():
                    p_name = line.split(':', 1)[1].strip()
                    if p_name:
                        gpus.append({
                            "name": p_name,
                            "load": 0,
                            "memoryTotal": 0,
                            "memoryUsed": 0
                        })
            except: pass

    # 3. macOS Brute Force (system_profiler)
    if not gpus and system == "Darwin":
        try:
            out = subprocess.check_output(['system_profiler', 'SPDisplaysDataType']).decode('utf-8')
            chip_name = ''
            vram_mb = 0
            for line in out.splitlines():
                line_str = line.strip()
                if line_str.startswith('Chipset Model:'):
                    chip_name = line_str.split(':', 1)[1].strip()
                elif 'VRAM' in line_str:
                    match = re.search(r'(\d+)\s*(MB|GB)', line_str, re.IGNORECASE)
                    if match:
                        val = int(match.group(1))
                        unit = match.group(2).upper()
                        vram_mb = val if unit == 'MB' else val * 1024
                if chip_name and vram_mb > 0:
                    gpus.append({
                        "name": chip_name,
                        "load": 0,
                        "memoryTotal": vram_mb,
                        "memoryUsed": 0
                    })
                    chip_name = ''
                    vram_mb = 0
            if not gpus and chip_name:
                gpus.append({"name": chip_name, "load": 0, "memoryTotal": 1536, "memoryUsed": 0})
        except: pass

    # 4. Windows Brute Force (WMIC / PowerShell)
    if not gpus and system == "Windows":
        try:
            out = subprocess.check_output('wmic path win32_VideoController get name,AdapterRAM /format:csv', shell=True).decode()
            for line in out.splitlines():
                line = line.strip()
                if not line or line.startswith('Node'): continue
                parts = line.split(',')
                # Format: Node, AdapterRAM, Name
                if len(parts) >= 3:
                    name = parts[2].strip()
                    # Clean up leading numbers like "0 VirtualBox..."
                    name = re.sub(r'^\d+\s+', '', name).strip()
                    try:
                        ram_bytes = int(parts[1].strip())
                        ram_mb = round(ram_bytes / (1024 * 1024))
                    except: ram_mb = 0

                    if name:
                        gpus.append({
                            "name": name,
                            "load": 0,
                            "memoryTotal": ram_mb,
                            "memoryUsed": 0
                        })
        except: pass

    if not gpus:
        gpus.append({
            "name": "GPU Genérica / Gráficos Integrados del Sistema",
            "load": 0,
            "memoryTotal": 0,
            "memoryUsed": 0
        })

    return gpus

def send_data(ws):
    while True:
        try:
            sys_info = get_system_info()
            data = {
                "system_info": sys_info,
                "os": sys_info,
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
