import json
import statistics
import time
import urllib.request
import urllib.error
import http.cookiejar
from urllib.request import build_opener, HTTPCookieProcessor, Request

BASE_URL = "http://127.0.0.1:8080/api/v1"
REQUESTS_COUNT = 1000

cookies = http.cookiejar.CookieJar()
opener = build_opener(HTTPCookieProcessor(cookies))


def request(method: str, path: str, payload: dict | None = None):
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    with opener.open(req, timeout=10) as response:
        body = response.read().decode("utf-8")
        return response.status, body


def measure(name: str, method: str, path: str, count: int):
    durations = []
    errors = 0

    for _ in range(count):
        start = time.perf_counter()
        try:
            request(method, path)
        except Exception:
            errors += 1
        finally:
            durations.append((time.perf_counter() - start) * 1000)

    durations_sorted = sorted(durations)
    p95 = durations_sorted[int(len(durations_sorted) * 0.95) - 1]

    print(f"{name}")
    print(f"  requests: {count}")
    print(f"  errors: {errors}")
    print(f"  avg_ms: {statistics.mean(durations):.2f}")
    print(f"  p95_ms: {p95:.2f}")
    print(f"  max_ms: {max(durations):.2f}")
    print()


if __name__ == "__main__":
    username = f"load_user_{int(time.time())}"
    password = "verystrong123"

    request("POST", "/auth/register", {
        "username": username,
        "password": password,
        "full_name": "Load Test User",
    })

    request("POST", "/auth/login", {
        "username": username,
        "password": password,
    })

    measure("GET /health", "GET", "/health", REQUESTS_COUNT)
    measure("GET /contests", "GET", "/contests", REQUESTS_COUNT)
    measure("GET /submissions", "GET", "/submissions", REQUESTS_COUNT)