# app/services/hardware_service.py
"""
Lightweight Hardware & Resource Inspector.
Gathers memory (RAM) and GPU/VRAM statistics with zero heavy dependencies (no psutil, no torch)
for peer clustering and workstation resource identification.
"""

import os
import sys
import time
import shutil
import ctypes
import subprocess
from typing import Dict, Any, Tuple, Optional

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


class HardwareService:
    def __init__(self):
        self._cached_specs: Optional[Dict[str, Any]] = None
        self._cached_gpu: Optional[Tuple[str, Optional[float], Optional[float]]] = None
        self._last_checked = 0
        self._cache_ttl = 30  # Cache for 30 seconds to minimize queries

    def get_hardware_specs(self) -> Dict[str, Any]:
        """Return cached or freshly polled lightweight hardware specs."""
        now = time.time()
        if self._cached_specs is not None and (now - self._last_checked < self._cache_ttl):
            return self._cached_specs

        ram_total, ram_avail = self._get_ram()
        gpu_name, vram_total, vram_avail = self._get_gpu()

        # Build clean concise summary badge (e.g. "RTX 3080 (10 GB VRAM) • 32 GB RAM")
        summary_parts = []
        if gpu_name and gpu_name != "Integrated / CPU":
            clean_gpu = (
                gpu_name.replace("NVIDIA GeForce ", "")
                .replace("NVIDIA ", "")
                .replace("AMD Radeon ", "Radeon ")
                .replace("Graphics", "")
                .strip()
            )
            if vram_total:
                summary_parts.append(f"{clean_gpu} ({vram_total:g} GB VRAM)")
            else:
                summary_parts.append(clean_gpu)
        else:
            summary_parts.append(gpu_name or "CPU")

        if ram_total > 0:
            summary_parts.append(f"{ram_total:g} GB RAM")

        summary = " • ".join(summary_parts)

        specs = {
            "ram_total_gb": ram_total,
            "ram_avail_gb": ram_avail,
            "gpu_name": gpu_name,
            "vram_total_gb": vram_total,
            "vram_avail_gb": vram_avail,
            "summary": summary,
            "os": sys.platform
        }
        self._cached_specs = specs
        self._last_checked = now
        return specs

    def _get_ram(self) -> Tuple[float, float]:
        """Get total and available RAM in GB with zero heavy dependencies."""
        if sys.platform == "win32":
            try:
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    total_gb = round(stat.ullTotalPhys / (1024**3), 1)
                    avail_gb = round(stat.ullAvailPhys / (1024**3), 1)
                    return total_gb, avail_gb
            except Exception:
                pass

        elif sys.platform.startswith("linux"):
            try:
                total_kb = 0
                avail_kb = 0
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            total_kb = int(line.split()[1])
                        elif line.startswith("MemAvailable:"):
                            avail_kb = int(line.split()[1])
                if total_kb > 0:
                    return round(total_kb / (1024**2), 1), round(avail_kb / (1024**2), 1)
            except Exception:
                pass

        elif sys.platform == "darwin":
            try:
                out = subprocess.check_output(
                    ["sysctl", "-n", "hw.memsize"],
                    timeout=1.0, text=True,
                    creationflags=CREATE_NO_WINDOW
                ).strip()
                total_gb = round(int(out) / (1024**3), 1)
                return total_gb, round(total_gb * 0.5, 1)
            except Exception:
                pass

        return 0.0, 0.0

    def _get_gpu(self) -> Tuple[str, Optional[float], Optional[float]]:
        """Query GPU model and VRAM in GB using nvidia-smi, winreg, or lspci."""
        if self._cached_gpu is not None:
            return self._cached_gpu

        # 1. First try nvidia-smi (works on Windows & Linux with NVIDIA GPUs)
        if shutil.which("nvidia-smi"):
            try:
                out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
                    timeout=1.5,
                    text=True,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW
                ).strip()
                if out:
                    line = out.splitlines()[0]
                    parts = [p.strip() for p in line.split(",")]
                    name = parts[0]
                    total_gb = round(float(parts[1]) / 1024.0, 1)
                    free_gb = round(float(parts[2]) / 1024.0, 1) if len(parts) > 2 else None
                    self._cached_gpu = (name, total_gb, free_gb)
                    return self._cached_gpu
            except Exception:
                pass

        # 2. Windows: Fast zero-process winreg query
        if sys.platform == "win32":
            try:
                import winreg
                path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as base_key:
                    for i in range(50):
                        try:
                            sub_name = winreg.EnumKey(base_key, i)
                            with winreg.OpenKey(base_key, sub_name) as sub_key:
                                try:
                                    desc, _ = winreg.QueryValueEx(sub_key, "DriverDesc")
                                    if desc and desc not in ("Basic Render Driver", "Microsoft Basic Display Adapter"):
                                        self._cached_gpu = (desc, None, None)
                                        return self._cached_gpu
                                except FileNotFoundError:
                                    pass
                        except OSError:
                            break
            except Exception:
                pass

        # 3. Linux fallback: lspci
        if sys.platform.startswith("linux") and shutil.which("lspci"):
            try:
                out = subprocess.check_output(
                    ["lspci"],
                    timeout=1.5, text=True,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW
                )
                for line in out.splitlines():
                    if "VGA" in line or "3D" in line:
                        clean = line.split(":")[-1].strip()
                        self._cached_gpu = (clean, None, None)
                        return self._cached_gpu
            except Exception:
                pass

        self._cached_gpu = ("Integrated / CPU", None, None)
        return self._cached_gpu


hardware_service = HardwareService()
