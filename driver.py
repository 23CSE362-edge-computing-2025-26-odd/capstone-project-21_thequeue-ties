# driver.py
from simulation import WorkspaceSimulation

if __name__ == "__main__":
    sim = WorkspaceSimulation(
        broker="localhost",
        port=1883,
        keepalive=60,
        tick_seconds=1.0,   # send once per second
    )
    sim.run(max_ticks=45)
