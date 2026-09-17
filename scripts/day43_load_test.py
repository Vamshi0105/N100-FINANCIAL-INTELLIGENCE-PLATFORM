import threading
import time
import urllib.request
import json
import statistics

URL = "http://127.0.0.1:8000/api/v1/screener?min_roe=15"

results = []
errors = []
lock = threading.Lock()


def make_request(request_id):
    start = time.perf_counter()

    try:
        with urllib.request.urlopen(URL, timeout=10) as response:
            body = response.read()
            status = response.status

        elapsed = time.perf_counter() - start
        data = json.loads(body)

        with lock:
            results.append({
                "id": request_id,
                "status": status,
                "elapsed": elapsed,
                "count": data.get("count"),
            })

    except Exception as exc:
        elapsed = time.perf_counter() - start

        with lock:
            errors.append({
                "id": request_id,
                "elapsed": elapsed,
                "error": str(exc),
            })


def main():
    print("=" * 60)
    print("DAY 43 - FASTAPI CONCURRENT LOAD TEST")
    print("=" * 60)
    print(f"URL: {URL}")
    print("Concurrent requests: 10")
    print()

    threads = []
    overall_start = time.perf_counter()

    for i in range(1, 11):
        thread = threading.Thread(
            target=make_request,
            args=(i,)
        )
        threads.append(thread)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    overall_elapsed = time.perf_counter() - overall_start

    print("RESULTS")
    print("-" * 60)

    for result in sorted(results, key=lambda x: x["id"]):
        print(
            f"Request {result['id']:02d}: "
            f"{result['elapsed']:.4f}s | "
            f"HTTP {result['status']} | "
            f"count={result['count']}"
        )

    if errors:
        print()
        print("ERRORS")
        print("-" * 60)

        for error in errors:
            print(
                f"Request {error['id']:02d}: "
                f"{error['elapsed']:.4f}s | "
                f"{error['error']}"
            )

    print()
    print("SUMMARY")
    print("-" * 60)

    print(f"Successful requests : {len(results)}/10")
    print(f"Failed requests     : {len(errors)}/10")
    print(f"Total elapsed       : {overall_elapsed:.4f}s")

    if results:
        timings = [r["elapsed"] for r in results]

        print(f"Average response    : {statistics.mean(timings):.4f}s")
        print(f"Minimum response    : {min(timings):.4f}s")
        print(f"Maximum response    : {max(timings):.4f}s")

    passed = (
        len(results) == 10
        and len(errors) == 0
        and overall_elapsed < 10
    )

    print()
    print("=" * 60)

    if passed:
        print("PASS - 10 concurrent requests completed within 10 seconds")
    else:
        print("FAIL - Load test target not met")

    print("=" * 60)


if __name__ == "__main__":
    main()