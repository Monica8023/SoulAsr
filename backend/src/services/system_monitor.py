from __future__ import annotations

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency
    psutil = None

try:
    import pynvml
except ImportError:  # pragma: no cover - optional dependency
    pynvml = None

from backend.src.schemas.system import CpuUsage, GpuUsage, MemoryUsage


class SystemMonitor:
    def get_cpu_usage(self) -> CpuUsage:
        if psutil is None:
            return CpuUsage(used_percent=0.0)
        return CpuUsage(used_percent=round(psutil.cpu_percent(interval=0.0), 2))

    def get_memory_usage(self) -> MemoryUsage:
        if psutil is None:
            return MemoryUsage(used_percent=0.0, used_mb=0.0, total_mb=0.0)
        memory = psutil.virtual_memory()
        return MemoryUsage(
            used_percent=round(memory.percent, 2),
            used_mb=round(memory.used / 1024 / 1024, 2),
            total_mb=round(memory.total / 1024 / 1024, 2),
        )

    def get_gpu_usage(self) -> GpuUsage:
        if pynvml is None:
            return GpuUsage()

        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="ignore")
            used_mb = round(memory.used / 1024 / 1024, 2)
            total_mb = round(memory.total / 1024 / 1024, 2)
            utilization = round((used_mb / total_mb) * 100, 2) if total_mb else 0.0
            return GpuUsage(
                available=True,
                name=name,
                used_mb=used_mb,
                total_mb=total_mb,
                utilization_percent=utilization,
            )
        except Exception:
            return GpuUsage()
        finally:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
