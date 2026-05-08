import subprocess
import xml.etree.ElementTree as ET


def _parse_int(value: str | None) -> int:
    if not value or value in {"N/A", "[Not Supported]"}:
        return 0
    token = value.strip().split()[0]
    try:
        return int(float(token))
    except ValueError:
        return 0


def _parse_processes(gpu_element: ET.Element) -> list[dict]:
    result: list[dict] = []
    processes = gpu_element.find("processes")
    if processes is None:
        return result

    for proc in processes.findall("process_info"):
        result.append(
            {
                "pid": _parse_int(proc.findtext("pid")),
                "name": proc.findtext("process_name") or "unknown",
                "memory_used": _parse_int(proc.findtext("used_memory")),
            }
        )
    return result


def collect_gpu_info() -> list[dict]:
    try:
        completed = subprocess.run(
            ["nvidia-smi", "-q", "-x"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []

    try:
        root = ET.fromstring(completed.stdout)
    except ET.ParseError:
        return []

    gpus: list[dict] = []
    for index, gpu_element in enumerate(root.findall("gpu")):
        fb_memory = gpu_element.find("fb_memory_usage")
        utilization = gpu_element.find("utilization")
        temperature = gpu_element.find("temperature")
        power = gpu_element.find("power_readings")

        gpus.append(
            {
                "index": index,
                "model": gpu_element.findtext("product_name") or "unknown",
                "uuid": gpu_element.findtext("uuid"),
                "memory_total": _parse_int(fb_memory.findtext("total") if fb_memory is not None else None),
                "memory_used": _parse_int(fb_memory.findtext("used") if fb_memory is not None else None),
                "memory_free": _parse_int(fb_memory.findtext("free") if fb_memory is not None else None),
                "utilization_gpu": _parse_int(
                    utilization.findtext("gpu_util") if utilization is not None else None
                ),
                "utilization_memory": _parse_int(
                    utilization.findtext("memory_util") if utilization is not None else None
                ),
                "temperature": _parse_int(
                    temperature.findtext("gpu_temp") if temperature is not None else None
                ),
                "power_usage": _parse_int(
                    power.findtext("power_draw") if power is not None else None
                ),
                "power_limit": _parse_int(
                    power.findtext("current_power_limit") if power is not None else None
                ),
                "processes": _parse_processes(gpu_element),
            }
        )

    return gpus
