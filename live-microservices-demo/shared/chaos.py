"""
Chaos Engineering Fault Injection Engine for Live Microservices Demo.
Allows injecting controlled faults (latency, error rate, CPU load, memory pressure, outage)
to verify that Synapse RiskOps observes anomalies, computes risk scores, and isolates root causes.
"""

import os
import time
import random
import threading
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("demo.chaos")


class ChaosEngine:
    def __init__(self, service_name: str = "service"):
        self.service_name = service_name
        self._lock = threading.Lock()
        self._active_faults: Dict[str, Dict[str, Any]] = {}
        self._cpu_threads: List[threading.Thread] = []
        self._cpu_stop_event = threading.Event()
        self._memory_buffers: List[bytearray] = []

    def get_status(self) -> Dict[str, Any]:
        """Return active faults and operational health."""
        with self._lock:
            self._cleanup_expired()
            faults = {k: {**v} for k, v in self._active_faults.items()}
        return {
            "service_name": self.service_name,
            "has_active_fault": len(faults) > 0,
            "active_faults": faults,
            "timestamp": time.time(),
        }

    def inject_fault(
        self,
        fault_type: str,
        duration_seconds: int = 120,
        intensity: float = 0.8,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Inject a fault into this microservice.
        Supported fault types:
        - 'latency': injects delay (intensity scales from 200ms to 4000ms)
        - 'error_rate': fails requests with HTTP 500 (probability = intensity)
        - 'cpu_spike': spins CPU worker threads
        - 'memory_leak': allocates memory buffers
        - 'service_outage': rejects all requests with HTTP 503
        """
        fault_type = fault_type.lower().strip()
        intensity = max(0.05, min(1.0, float(intensity)))
        duration_seconds = max(5, min(3600, int(duration_seconds)))
        now = time.time()
        expires_at = now + duration_seconds

        with self._lock:
            self._cleanup_expired()
            self._active_faults[fault_type] = {
                "fault_type": fault_type,
                "intensity": intensity,
                "duration_seconds": duration_seconds,
                "injected_at": now,
                "expires_at": expires_at,
                "extra_params": extra_params or {},
            }

        if fault_type == "cpu_spike":
            self._start_cpu_spike(intensity, duration_seconds)
        elif fault_type == "memory_leak":
            self._allocate_memory(intensity)

        logger.warning(
            f"⚠️ Chaos fault '{fault_type}' injected into [{self.service_name}] "
            f"(intensity={intensity:.2f}, duration={duration_seconds}s)"
        )
        return self.get_status()

    def clear_faults(self) -> Dict[str, Any]:
        """Clear all active faults and restore normal baseline behavior."""
        with self._lock:
            self._active_faults.clear()
            self._cpu_stop_event.set()
            for t in self._cpu_threads:
                t.join(timeout=0.2)
            self._cpu_threads.clear()
            self._cpu_stop_event.clear()
            self._memory_buffers.clear()

        logger.info(f"✅ All chaos faults cleared for [{self.service_name}]. Baseline restored.")
        return self.get_status()

    def apply_runtime_faults(self):
        """
        Invoked on each incoming HTTP request.
        Applies latency, error rate, or raises outage exception if configured.
        """
        with self._lock:
            self._cleanup_expired()
            outage = self._active_faults.get("service_outage")
            error_fault = self._active_faults.get("error_rate")
            latency_fault = self._active_faults.get("latency")

        if outage:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail=f"Chaos: Service [{self.service_name}] is unavailable due to injected outage."
            )

        if error_fault:
            probability = error_fault["intensity"]
            if random.random() < probability:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=500,
                    detail=f"Chaos: Simulated internal failure in [{self.service_name}]."
                )

        if latency_fault:
            intensity = latency_fault["intensity"]
            # Delay between 0.3s and 3.5s based on intensity
            base_delay = 0.3 + (intensity * 3.2)
            jitter = random.uniform(-0.1, 0.2)
            actual_delay = max(0.1, base_delay + jitter)
            time.sleep(actual_delay)

    def _cleanup_expired(self):
        now = time.time()
        expired = [k for k, v in self._active_faults.items() if now >= v["expires_at"]]
        for k in expired:
            del self._active_faults[k]
            if k == "cpu_spike":
                self._cpu_stop_event.set()
                self._cpu_threads.clear()
            elif k == "memory_leak":
                self._memory_buffers.clear()
            logger.info(f"ℹ️ Chaos fault '{k}' on [{self.service_name}] expired naturally.")

    def _start_cpu_spike(self, intensity: float, duration_seconds: int):
        self._cpu_stop_event.set()
        self._cpu_threads.clear()
        self._cpu_stop_event.clear()
        num_workers = max(1, int(intensity * 4))
        for _ in range(num_workers):
            t = threading.Thread(
                target=self._cpu_worker,
                args=(intensity, duration_seconds),
                daemon=True,
            )
            self._cpu_threads.append(t)
            t.start()

    def _cpu_worker(self, intensity: float, duration_seconds: int):
        end_time = time.time() + duration_seconds
        busy_slice = 0.05 * intensity
        sleep_slice = 0.05 * (1.0 - intensity)
        while time.time() < end_time and not self._cpu_stop_event.is_set():
            start = time.time()
            while time.time() - start < busy_slice:
                _ = 3.14159 ** 2.71828 * random.random()
            if sleep_slice > 0:
                time.sleep(sleep_slice)

    def _allocate_memory(self, intensity: float):
        num_mb = int(120 * intensity)
        self._memory_buffers.clear()
        try:
            for _ in range(num_mb):
                self._memory_buffers.append(bytearray(1024 * 1024))
        except MemoryError:
            pass
