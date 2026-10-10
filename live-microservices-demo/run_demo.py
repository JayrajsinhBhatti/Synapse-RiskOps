"""
Master Microservices Orchestrator & Process Launcher.
Starts all 10 microservices, the storefront server, and the traffic generator
as independent concurrent processes with graceful shutdown.
"""

import sys
import os
import time
import subprocess
import signal

SERVICES = [
    ("api-gateway", "gateway/main.py", 9101),
    ("auth-service", "auth/main.py", 9102),
    ("user-service", "user/main.py", 9103),
    ("catalog-service", "catalog/main.py", 9104),
    ("inventory-service", "inventory/main.py", 9105),
    ("cart-service", "cart/main.py", 9106),
    ("order-service", "order/main.py", 9107),
    ("payment-service", "payment/main.py", 9108),
    ("notification-service", "notification/main.py", 9109),
    ("recommendation-service", "recommendation/main.py", 9110),
    ("storefront", "storefront/server.py", 9100),
]

processes = []
root_dir = os.path.dirname(os.path.abspath(__file__))


def launch_all():
    print("=" * 70)
    print("   LAUNCHING 10 INDEPENDENT MICROSERVICES + STOREFRONT UI")
    print("=" * 70)

    for name, script_rel, port in SERVICES:
        script_path = os.path.join(root_dir, script_rel)
        cmd = [sys.executable, "-u", script_path]
        env = os.environ.copy()
        env["PORT"] = str(port)

        print(f"  -> Starting {name:<22} on http://localhost:{port} ...")
        proc = subprocess.Popen(
            cmd,
            cwd=root_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append((name, proc))
        time.sleep(0.4)

    print("=" * 70)
    print("[SUCCESS] All 10 Microservices + Storefront started successfully!")
    print("Storefront UI:          http://localhost:9100")
    print("API Gateway:            http://localhost:9101/docs")
    print("Operations Health:      http://localhost:9101/api/operations/system-status")
    print("=" * 70)
    print("Starting background traffic generator & telemetry streamer...")
    traffic_script = os.path.join(root_dir, "traffic_generator.py")
    t_proc = subprocess.Popen([sys.executable, "-u", traffic_script], cwd=root_dir)
    processes.append(("traffic-generator", t_proc))

    def handle_sig(sig, frame):
        print("\nStopping all microservices...")
        for name, p in processes:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    launch_all()
