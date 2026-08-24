import time
import os
import sys

_TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS_ROOT))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_TESTS_ROOT))

from app.db.production_read_adapter import ProductionReadAdapter

def main():
    adapter = ProductionReadAdapter()

    # Warmup
    try:
        adapter.get_unified_queue(limit=1)
    except Exception as e:
        print(f"Warmup failed: {e}")
        return

    n_iterations = 1000
    start = time.perf_counter()
    for _ in range(n_iterations):
        adapter.get_unified_queue(limit=1)
    end = time.perf_counter()

    duration = end - start
    print(f"Total time for {n_iterations} calls: {duration:.4f} seconds")
    print(f"Time per call: {(duration / n_iterations) * 1000:.4f} ms")

if __name__ == "__main__":
    main()
