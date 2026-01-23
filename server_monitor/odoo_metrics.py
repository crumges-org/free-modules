import math
import threading
import time
from collections import deque


def _percentile(values, percent):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * (percent / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    return values[f] + (values[c] - values[f]) * (k - f)


class OdooRequestMetrics:
    def __init__(self, window_seconds=60, max_requests=20000):
        self.window_seconds = max(window_seconds, 10)
        self.max_requests = max_requests
        self._lock = threading.Lock()
        self._buckets = deque()
        self._requests = deque()

    def set_window(self, window_seconds):
        self.window_seconds = max(window_seconds, 10)

    def record(self, path, method, status, duration_ms, exception=None):
        now = int(time.time())
        with self._lock:
            self._ensure_bucket(now)
            bucket = self._buckets[-1]
            bucket["count"] += 1
            bucket["sum_ms"] += duration_ms
            bucket["durations"].append(duration_ms)
            if status >= 400:
                bucket["errors"] += 1
            if 400 <= status < 500:
                bucket["status_4xx"] += 1
            if status >= 500:
                bucket["status_5xx"] += 1
            if exception:
                bucket["exceptions"][exception] = bucket["exceptions"].get(exception, 0) + 1

            self._requests.append(
                {
                    "ts": now,
                    "path": path or "-",
                    "method": method or "",
                    "status": status,
                    "duration_ms": duration_ms,
                    "exception": exception,
                }
            )
            self._prune(now)

    def snapshot(self, history_length):
        now = int(time.time())
        window = max(history_length, 10)
        self.set_window(window)
        with self._lock:
            self._prune(now)
            bucket_map = {bucket["sec"]: bucket for bucket in self._buckets}

            labels = []
            requests_series = []
            error_rate_series = []
            status_4xx_series = []
            status_5xx_series = []
            p95_series = []
            p99_series = []

            for sec in range(now - window + 1, now + 1):
                bucket = bucket_map.get(sec)
                if bucket:
                    count = bucket["count"]
                    errors = bucket["errors"]
                    status_4xx = bucket["status_4xx"]
                    status_5xx = bucket["status_5xx"]
                    durations = bucket["durations"]
                else:
                    count = 0
                    errors = 0
                    status_4xx = 0
                    status_5xx = 0
                    durations = []

                labels.append(time.strftime("%M:%S", time.localtime(sec)))
                requests_series.append(count)
                error_rate_series.append(
                    (errors / count) * 100.0 if count else 0.0
                )
                status_4xx_series.append(
                    (status_4xx / count) * 100.0 if count else 0.0
                )
                status_5xx_series.append(
                    (status_5xx / count) * 100.0 if count else 0.0
                )
                p95_series.append(_percentile(durations, 95))
                p99_series.append(_percentile(durations, 99))

            total_requests = sum(requests_series)
            total_errors = sum(
                int(round(rate / 100.0 * count))
                for rate, count in zip(error_rate_series, requests_series)
            )
            all_durations = [
                req["duration_ms"] for req in self._requests if req["ts"] >= now - window
            ]
            avg_ms = (
                sum(all_durations) / len(all_durations)
                if all_durations
                else None
            )
            summary = {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": (total_errors / total_requests) * 100.0
                if total_requests
                else 0.0,
                "avg_ms": avg_ms,
                "p95_ms": _percentile(all_durations, 95),
                "p99_ms": _percentile(all_durations, 99),
            }

            slow_endpoints, top_errors = self._build_endpoint_stats(window, now)

        return {
            "labels": labels,
            "requests_per_s": requests_series,
            "error_rate": error_rate_series,
            "status_4xx_rate": status_4xx_series,
            "status_5xx_rate": status_5xx_series,
            "latency_p95": p95_series,
            "latency_p99": p99_series,
            "summary": summary,
            "slow_endpoints": slow_endpoints,
            "top_errors": top_errors,
        }

    def _build_endpoint_stats(self, window, now):
        per_path = {}
        error_counts = {}
        cutoff = now - window
        for req in self._requests:
            if req["ts"] < cutoff:
                continue
            key = req["path"]
            entry = per_path.setdefault(
                key, {"count": 0, "durations": [], "errors": 0}
            )
            entry["count"] += 1
            entry["durations"].append(req["duration_ms"])
            if req["status"] >= 400:
                entry["errors"] += 1

            if req["status"] >= 500 or req["exception"]:
                err_key = req["exception"] or f"HTTP {req['status']}"
                error_counts[err_key] = error_counts.get(err_key, 0) + 1

        slow_endpoints = []
        for path, entry in per_path.items():
            durations = entry["durations"]
            avg_ms = sum(durations) / len(durations) if durations else None
            slow_endpoints.append(
                {
                    "path": path,
                    "count": entry["count"],
                    "avg_ms": avg_ms,
                    "p95_ms": _percentile(durations, 95),
                    "p99_ms": _percentile(durations, 99),
                    "error_rate": (entry["errors"] / entry["count"]) * 100.0
                    if entry["count"]
                    else 0.0,
                }
            )
        slow_endpoints.sort(
            key=lambda row: row["avg_ms"] if row["avg_ms"] is not None else 0,
            reverse=True,
        )

        top_errors = [
            {"name": name, "count": count}
            for name, count in sorted(
                error_counts.items(), key=lambda item: item[1], reverse=True
            )
        ]

        return slow_endpoints[:8], top_errors[:6]

    def _ensure_bucket(self, sec):
        if not self._buckets:
            self._buckets.append(self._new_bucket(sec))
            return
        last_sec = self._buckets[-1]["sec"]
        if sec <= last_sec:
            return
        for next_sec in range(last_sec + 1, sec + 1):
            self._buckets.append(self._new_bucket(next_sec))

    def _prune(self, now):
        cutoff = now - self.window_seconds
        while self._buckets and self._buckets[0]["sec"] < cutoff:
            self._buckets.popleft()
        while self._requests and self._requests[0]["ts"] < cutoff:
            self._requests.popleft()
        while len(self._requests) > self.max_requests:
            self._requests.popleft()

    def _new_bucket(self, sec):
        return {
            "sec": sec,
            "count": 0,
            "errors": 0,
            "status_4xx": 0,
            "status_5xx": 0,
            "sum_ms": 0.0,
            "durations": [],
            "exceptions": {},
        }


REQUEST_METRICS = OdooRequestMetrics()
