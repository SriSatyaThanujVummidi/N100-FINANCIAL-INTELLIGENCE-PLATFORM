"""Day 43 -- Load test: 10 concurrent /screener calls via threading. Requires the API
server running on port 8000 (python -m uvicorn src.api.main:app --port 8000)."""
import time
import threading
import requests

URL = "http://localhost:8000/api/v1/screener"
PARAMS = {"min_roe": 15}
N_CONCURRENT = 10

results = []
lock = threading.Lock()


def call_screener(i):
    start = time.perf_counter()
    resp = requests.get(URL, params=PARAMS, timeout=10)
    duration = time.perf_counter() - start
    with lock:
        entry = {"thread": i, "status": resp.status_code, "duration_s": round(duration, 3)}
        if resp.status_code != 200:
            entry["error_body"] = resp.text[:300]
        results.append(entry)


threads = [threading.Thread(target=call_screener, args=(i,)) for i in range(N_CONCURRENT)]
overall_start = time.perf_counter()
for t in threads:
    t.start()
for t in threads:
    t.join()
overall_duration = time.perf_counter() - overall_start

print(f"\n{N_CONCURRENT} concurrent /screener calls:")
for r in sorted(results, key=lambda x: x["thread"]):
    print(f"  Thread {r['thread']}: {r['status']} in {r['duration_s']}s")

for r in results:
    if r["status"] != 200:
        print(f"  ERROR thread {r['thread']}: {r.get('error_body')}")

print(f"\nAll {N_CONCURRENT} completed in {round(overall_duration, 3)}s (target: <10s)")
print(f"Slowest individual call: {max(r['duration_s'] for r in results)}s")
all_succeeded = all(r["status"] == 200 for r in results)
print(f"All requests succeeded (200): {all_succeeded}")
print("PASS" if overall_duration < 10 and all_succeeded else "FAIL")