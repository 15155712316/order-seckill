# diag_machine_code.py
import platform
import subprocess
import hashlib
import uuid
import json

def get_raw_wmic_output(command_parts):
    """执行WMIC命令并返回原始、未经处理的stdout。"""
    try:
        process = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW # 防止弹出黑窗
        )
        return process.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return f"ERROR: {e}"

def parse_wmic_output(output):
    """从WMIC输出中解析出我们想要的值。"""
    if "ERROR" in output:
        return ""
    lines = output.strip().splitlines()
    if len(lines) > 1:
        return lines[1].strip()
    return ""

print("="*30)
print("   机器码生成过程诊断工具")
print("="*30)
print(f"Python版本: {platform.python_version()} ({platform.architecture()[0]})")
print("-" * 30)

results = {}

# 1. 计算机名
key = "computer_name"
value = platform.node()
results[key] = value
print(f"[1] {key}:\n    -> '{value}'")

# 2. 处理器信息
key = "processor"
value = platform.processor()
results[key] = value
print(f"[2] {key}:\n    -> '{value}'")

# 3. 系统信息
key = "system_info"
value = f"{platform.system()}-{platform.machine()}"
results[key] = value
print(f"[3] {key}:\n    -> '{value}'")

if platform.system() == "Windows":
    # 4.1 主板序列号
    key = "motherboard_serial"
    raw_output = get_raw_wmic_output(['wmic', 'baseboard', 'get', 'serialnumber'])
    parsed_value = parse_wmic_output(raw_output)
    results[key] = parsed_value
    print(f"[4.1] {key}:\n    -> RAW: '{repr(raw_output)}'\n    -> PARSED: '{parsed_value}'")

    # 4.2 CPU序列号
    key = "cpu_serial"
    raw_output = get_raw_wmic_output(['wmic', 'cpu', 'get', 'processorid'])
    parsed_value = parse_wmic_output(raw_output)
    results[key] = parsed_value
    print(f"[4.2] {key}:\n    -> RAW: '{repr(raw_output)}'\n    -> PARSED: '{parsed_value}'")

    # 4.3 硬盘序列号
    key = "disk_serial"
    raw_output = get_raw_wmic_output(['wmic', 'diskdrive', 'where', 'index=0', 'get', 'serialnumber'])
    parsed_value = parse_wmic_output(raw_output)
    results[key] = parsed_value
    print(f"[4.3] {key}:\n    -> RAW: '{repr(raw_output)}'\n    -> PARSED: '{parsed_value}'")

# 5. MAC地址补充
if len(results) < 2:
    key = "mac_address"
    value = hex(uuid.getnode())
    results[key] = value
    print(f"[5] {key} (补充):\n    -> '{value}'")

print("-" * 30)

# 6. 组合所有信息
hardware_info = {k: v for k, v in results.items() if v}
print(f"[6] 最终用于哈希的硬件信息字典:\n    -> {json.dumps(hardware_info, indent=4)}")

sorted_keys = sorted(hardware_info.keys())
combined_parts = [f"{key}:{hardware_info[key]}" for key in sorted_keys]
combined_info = "|".join(combined_parts)
print(f"[7] 排序并组合后的最终字符串 (哈希前):\n    -> '{combined_info}'")

# 8. 生成最终机器码
machine_code = hashlib.md5(combined_info.encode('utf-8')).hexdigest()[:16].upper()
print(f"[8] 最终生成的16位大写机器码:\n    -> {machine_code}")
print("=" * 30)