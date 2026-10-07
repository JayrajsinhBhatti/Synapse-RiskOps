"""
Shared Chaos Engineering Fault Injection Engine for live microservices.
Supports CPU spike, memory leak, artificial latency, error rate injection, and crash simulation.
"""

import os
import time
import threading
import logging
import random
from typing import Dict, Any, List

logger = logging.getLogger("chaos")


class ChaosEngine:
    def __init__(self, service_name: str = "service"):
        self.service_name = service_name
        self._lock = threading.Lock()
        self._active_faults: Dict[str, Dict[str, Any]] = {}
        self._cpu_threads: List[threading.Thread] = []
        self._cpu_stop_event = threading.Event()
        self._memory_buffers: List[bytearray] = []

    def inject_fault(self, fault_type: str, duration_seconds: int = 120, intensity: float = 0.8) -> Dict[str, Any]:
        """Inject a chaos fault."""
        fault_type = fault_type.lower()
        intensity = max(0.01, min(1.0, float(intensity)))
        expires_at = time.time() + duration_seconds

        if fault_type == "crash":
            logger.critical(f"Chaos crash fault triggered on {self.service_name}! Terminating process...")
            threading.Thread(target=self._delayed_crash, daemon=True).start()
            return {"status": "crashing", "service": self.service_name}

        with self._lock:
            self._cleanup_expired()
            self._active_faults[fault_type] = {
                "fault_type": fault_type,
                "intensity": intensity,
                "duration_seconds": duration_seconds,
                "injected_at": time.time(),
                "expires_at": expires_at,
            }

        if fault_type == "cpu_spike":
            self._start_cpu_spike(intensity, duration_seconds)
        elif fault_type == "memory_leak":
            self._allocate_memory(intensity)

        logger.warning(
            f"Chaos fault '{fault_type}' injected into {self.service_name} "
            f"(intensity={intensity}, duration={duration_seconds}s)"
        )
        return self.get_status()

    def _delayed_crash(self):
        time.sleep(0.5)
        os._exit(1)

    def _start_cpu_spike(self, intensity: float, duration_seconds: int):
        self._cpu_stop_event.set()
        for t in self._cpu_threads:
            t.join(timeout=0.1)
        self._cpu_threads.clear()
        self._cpu_stop_event.clear()

        # Spin up threads based on intensity
        thread_count = max(1, int(intensity * 4))
        for _ in range(thread_count):
            t = threading.Thread(target=self._cpu_worker, args=(intensity, duration_seconds), daemon=True)
            self._cpu_threads.append(t)
            t.start()

    def _cpu_worker(self, intensity: float, duration_seconds: int):
        end_time = time.time() + duration_seconds
        busy_slice = 0.05 * intensity
        sleep_slice = 0.05 * (1.0 - intensity)
        while time.time() < end_time and not self._cpu_stop_event.is_set():
            busy_start = time.time()
            while time.time() - busy_start < busy_slice:
                _ = 3.14159 ** 2.71828 * random.random()
            if sleep_slice > 0:
                time.sleep(sleep_slice)

    def _allocate_memory(self, intensity: float):
        # Allocate chunks of memory (approx 30MB * intensity, up to ~150MB)
        total_mb = int(150 * intensity)
        self._memory_buffers.clear()
        try:
            for _ in range(total_mb):
                self._memory_buffers.append(bytearray(1024 * 1024))
        except MemoryError:
            logger.error("Out of memory during chaos memory allocation")

    def _cleanup_expired(self):
        now = time.time()
        expired = [k for k, v in self._active_faults.items() if now >= v["expires_at"]]
        for k in expired:
            logger.info(f"Chaos fault '{k}' on {self.service_name} has expired.")
            del self._active_faults[k]
            if k == "cpu_spike":
                self._cpu_stop_event.set()
            elif k == "memory_leak":
                self._memory_buffers.clear()

    def get_latency_delay(self) -> float:
        """Returns extra latency delay in seconds if latency fault is active."""
        with self._lock:
            self._cleanup_expired()
            fault = self._active_faults.get("latency")
            if fault:
                # Intensity 1.0 -> 3.0s delay, 0.5 -> 1.5s delay
                return fault["intensity"] * 3.0
            timeout_fault = self._active_faults.get("dependency_timeout")
            if timeout_fault:
                return timeout_fault["intensity"] * 5.0
        return 0.0

    def should_inject_error(self) -> bool:
        """Returns True if request should fail due to error_rate fault."""
        with self._lock:
            self._cleanup_expired()
            fault = self._active_faults.get("error_rate")
            if fault:
                return random.random() < fault["intensity"]
        return False

    def clear_faults(self) -> Dict[str, Any]:
        """Clears all active faults."""
        with self._lock:
            self._active_faults.clear()
            self._cpu_stop_event.set()
            self._cpu_threads.clear()
            self._memory_buffers.clear()
        logger.info(f"All chaos faults cleared on {self.service_name}")
        return {"status": "cleared", "active_faults": {}}

    def get_status(self) -> Dict[str, Any]:
        """Returns active faults status."""
        with self._lock:
            self._cleanup_expired()
            now = time.time()
            faults = {}
            for k, v in self._active_faults.items():
                faults[k] = {
                    "fault_type": v["fault_type"],
                    "intensity": v["intensity"],
                    "remaining_seconds": max(0, int(v["expires_at"] - now)),
                }
            return {
                "service": self.service_name,
                "active_faults_count": len(faults),
                "active_faults": faults,
            }
