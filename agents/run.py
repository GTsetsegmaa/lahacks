"""Start all five uAgents in parallel subprocesses.

Each agent.run() call is blocking, so we launch them as separate processes
and keep this script alive as a supervisor. If any process exits unexpectedly,
the whole group is terminated (fail-fast to surface errors clearly in Docker).
"""
from __future__ import annotations

import signal
import subprocess
import sys
import time

AGENTS = [
    "agents.coordinator.agent",
    "agents.demand_planning.agent",
    "agents.inventory_manager.agent",
    "agents.market_intelligence.agent",
    "agents.shipment_analyst.agent",
]


def main() -> None:
    procs: list[subprocess.Popen[bytes]] = []

    def shutdown(signum: int, _frame: object) -> None:
        for p in procs:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    for module in AGENTS:
        p = subprocess.Popen([sys.executable, "-m", module])
        procs.append(p)
        print(f"started {module} (pid={p.pid})", flush=True)

    # Poll; if any agent exits, tear everything down so Docker restarts the container.
    while True:
        for p in procs:
            if p.poll() is not None:
                print(f"agent pid={p.pid} exited with code {p.returncode} — shutting down", flush=True)
                for other in procs:
                    other.terminate()
                sys.exit(p.returncode or 1)
        time.sleep(2)


if __name__ == "__main__":
    main()
