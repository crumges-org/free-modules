import json
import os
import shutil
import socket
import subprocess
import time
from datetime import timedelta

try:
    import psutil
except ImportError:  # pragma: no cover - handled at runtime
    psutil = None

from odoo import fields
from odoo.http import request
from odoo.tools import config as odoo_config

from ..odoo_metrics import REQUEST_METRICS

DEFAULT_INTERVAL_MS = 1000
DEFAULT_HISTORY_LENGTH = 60
DEFAULT_PROCESS_INTERVAL_MS = 5000
DEFAULT_PROCESS_LIMIT = 5
DEFAULT_GPU_INTERVAL_MS = 2000
DEFAULT_PG_INTERVAL_MS = 2000
DEFAULT_PG_HISTORY_LENGTH = 60
DEFAULT_PG_SLOW_QUERY_SECONDS = 5
DEFAULT_PG_ALERT_CACHE_HIT_MIN = 95
DEFAULT_PG_ALERT_IDLE_IN_TX = 1
DEFAULT_PG_ALERT_LOCKS_WAITING = 1
DEFAULT_PG_ALERT_CONN_PCT = 80
DEFAULT_ODOO_INTERVAL_MS = 2000
DEFAULT_ODOO_HISTORY_LENGTH = 60
DEFAULT_ODOO_ERROR_WINDOW_MINUTES = 60
DEFAULT_ODOO_CRON_RUNNING_SECONDS = 300
DEFAULT_ODOO_LOG_LINES = 200
SAMPLE_TTL_SECONDS = 1.0

_CACHE = {"timestamp": 0.0, "payload": None}
_USER_NET_STATE = {}
_USER_DISK_STATE = {}
_PROCESS_CACHE = {"timestamp": 0.0, "payload": None}
_GPU_CACHE = {"timestamp": 0.0, "payload": None}
_PG_CACHE = {"timestamp": 0.0, "payload": None}


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_list(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class ServerMonitorBase:
    def _get_config(self):
        icp = request.env["ir.config_parameter"].sudo()
        interval_ms = _parse_int(
            icp.get_param("server_monitor.interval_ms"), DEFAULT_INTERVAL_MS
        )
        history_length = _parse_int(
            icp.get_param("server_monitor.history_length"), DEFAULT_HISTORY_LENGTH
        )
        pg_interval_ms = _parse_int(
            icp.get_param("server_monitor.pg_interval_ms"),
            DEFAULT_PG_INTERVAL_MS,
        )
        pg_history_length = _parse_int(
            icp.get_param("server_monitor.pg_history_length"),
            DEFAULT_PG_HISTORY_LENGTH,
        )
        pg_slow_query_seconds = _parse_int(
            icp.get_param("server_monitor.pg_slow_query_seconds"),
            DEFAULT_PG_SLOW_QUERY_SECONDS,
        )
        pg_alert_cache_hit_min = _parse_int(
            icp.get_param("server_monitor.pg_alert_cache_hit_min"),
            DEFAULT_PG_ALERT_CACHE_HIT_MIN,
        )
        pg_alert_idle_in_tx = _parse_int(
            icp.get_param("server_monitor.pg_alert_idle_in_tx"),
            DEFAULT_PG_ALERT_IDLE_IN_TX,
        )
        pg_alert_locks_waiting = _parse_int(
            icp.get_param("server_monitor.pg_alert_locks_waiting"),
            DEFAULT_PG_ALERT_LOCKS_WAITING,
        )
        pg_alert_conn_pct = _parse_int(
            icp.get_param("server_monitor.pg_alert_conn_pct"),
            DEFAULT_PG_ALERT_CONN_PCT,
        )
        odoo_interval_ms = _parse_int(
            icp.get_param("server_monitor.odoo_interval_ms"),
            DEFAULT_ODOO_INTERVAL_MS,
        )
        odoo_history_length = _parse_int(
            icp.get_param("server_monitor.odoo_history_length"),
            DEFAULT_ODOO_HISTORY_LENGTH,
        )
        odoo_error_window_minutes = _parse_int(
            icp.get_param("server_monitor.odoo_error_window_minutes"),
            DEFAULT_ODOO_ERROR_WINDOW_MINUTES,
        )
        odoo_cron_running_seconds = _parse_int(
            icp.get_param("server_monitor.odoo_cron_running_seconds"),
            DEFAULT_ODOO_CRON_RUNNING_SECONDS,
        )
        odoo_log_lines = _parse_int(
            icp.get_param("server_monitor.odoo_log_lines"),
            DEFAULT_ODOO_LOG_LINES,
        )
        process_interval_ms = _parse_int(
            icp.get_param("server_monitor.process_interval_ms"),
            DEFAULT_PROCESS_INTERVAL_MS,
        )
        process_limit = _parse_int(
            icp.get_param("server_monitor.process_limit"), DEFAULT_PROCESS_LIMIT
        )
        gpu_interval_ms = _parse_int(
            icp.get_param("server_monitor.gpu_interval_ms"),
            DEFAULT_GPU_INTERVAL_MS,
        )
        adapters_include = _parse_list(
            icp.get_param("server_monitor.adapters_include")
        )
        return {
            "interval_ms": max(interval_ms, 250),
            "history_length": max(history_length, 10),
            "pg_interval_ms": max(pg_interval_ms, 1000),
            "pg_history_length": max(pg_history_length, 10),
            "pg_slow_query_seconds": max(pg_slow_query_seconds, 1),
            "pg_alert_cache_hit_min": max(pg_alert_cache_hit_min, 1),
            "pg_alert_idle_in_tx": max(pg_alert_idle_in_tx, 0),
            "pg_alert_locks_waiting": max(pg_alert_locks_waiting, 0),
            "pg_alert_conn_pct": max(pg_alert_conn_pct, 1),
            "odoo_interval_ms": max(odoo_interval_ms, 1000),
            "odoo_history_length": max(odoo_history_length, 10),
            "odoo_error_window_minutes": max(odoo_error_window_minutes, 5),
            "odoo_cron_running_seconds": max(odoo_cron_running_seconds, 30),
            "odoo_log_lines": max(odoo_log_lines, 20),
            "process_interval_ms": max(process_interval_ms, 1000),
            "process_limit": max(process_limit, 1),
            "gpu_interval_ms": max(gpu_interval_ms, 1000),
            "adapters_include": adapters_include,
        }

    def _get_base_payload(self, adapters_include):
        now = time.time()
        cached = _CACHE.get("payload")
        if cached and (now - _CACHE.get("timestamp", 0.0)) < SAMPLE_TTL_SECONDS:
            return cached

        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
        cpu_percent = (
            sum(cpu_per_core) / len(cpu_per_core) if cpu_per_core else 0.0
        )
        cpu_freq = psutil.cpu_freq()
        cpu_stats = psutil.cpu_stats()
        loadavg = None
        try:
            loadavg = os.getloadavg()
        except (AttributeError, OSError):
            loadavg = None

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disks = self._get_disk_partitions()
        if not disks:
            root_path = os.path.abspath(os.sep)
            disk = psutil.disk_usage(root_path)
            disks = [
                {
                    "mountpoint": root_path,
                    "device": root_path,
                    "fstype": "",
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent,
                }
            ]

        disk_io = self._get_disk_io()
        net_io = psutil.net_io_counters(pernic=True)
        net_stats = psutil.net_if_stats()
        net_addrs = psutil.net_if_addrs()
        adapters = []
        for name, counters in net_io.items():
            if adapters_include and name not in adapters_include:
                continue
            stats = net_stats.get(name)
            if stats and not stats.isup:
                continue
            ips = []
            for addr in net_addrs.get(name, []):
                if addr.family in (socket.AF_INET, socket.AF_INET6):
                    ips.append(addr.address)
            adapters.append(
                {
                    "name": name,
                    "bytes_sent": counters.bytes_sent,
                    "bytes_recv": counters.bytes_recv,
                    "speed_mbps": getattr(stats, "speed", 0) if stats else 0,
                    "mtu": getattr(stats, "mtu", 0) if stats else 0,
                    "duplex": self._format_duplex(stats),
                    "ips": ips,
                }
            )
        adapters.sort(key=lambda item: item["name"])

        boot_time = psutil.boot_time()
        payload = {
            "timestamp": now,
            "cpu_percent": cpu_percent,
            "cpu_per_core": cpu_per_core,
            "cpu_freq": self._cpu_freq_payload(cpu_freq),
            "cpu_stats": cpu_stats._asdict() if cpu_stats else {},
            "loadavg": list(loadavg) if loadavg else [],
            "memory": {
                "total": memory.total,
                "used": memory.used,
                "percent": memory.percent,
                "available": getattr(memory, "available", 0),
                "free": getattr(memory, "free", 0),
                "buffers": getattr(memory, "buffers", 0),
                "cached": getattr(memory, "cached", 0),
                "shared": getattr(memory, "shared", 0),
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent,
                "sin": getattr(swap, "sin", 0),
                "sout": getattr(swap, "sout", 0),
            },
            "disks": disks,
            "disk_io": disk_io,
            "network": adapters,
            "system": {
                "boot_time": boot_time,
                "uptime": max(now - boot_time, 0.0),
            },
            "sensors": self._get_sensors_payload(),
        }
        _CACHE["timestamp"] = now
        _CACHE["payload"] = payload
        return payload

    def _get_disk_partitions(self):
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (OSError, PermissionError):
                continue
            disks.append(
                {
                    "mountpoint": part.mountpoint,
                    "device": part.device,
                    "fstype": part.fstype or "",
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            )
        return disks

    def _get_disk_io(self):
        io_counters = psutil.disk_io_counters(perdisk=True)
        disk_io = []
        if not io_counters:
            return disk_io
        for name, counters in io_counters.items():
            info = counters._asdict()
            info["name"] = name
            disk_io.append(info)
        disk_io.sort(key=lambda item: item["name"])
        return disk_io

    def _cpu_freq_payload(self, cpu_freq):
        if not cpu_freq:
            return {}
        return {
            "current": cpu_freq.current,
            "min": cpu_freq.min,
            "max": cpu_freq.max,
        }

    def _format_duplex(self, stats):
        if not stats:
            return "unknown"
        duplex_map = {
            getattr(psutil, "NIC_DUPLEX_FULL", object()): "full",
            getattr(psutil, "NIC_DUPLEX_HALF", object()): "half",
            getattr(psutil, "NIC_DUPLEX_UNKNOWN", object()): "unknown",
        }
        return duplex_map.get(stats.duplex, "unknown")

    def _get_sensors_payload(self):
        payload = {"temperatures": [], "fans": [], "battery": None}
        try:
            temperatures = psutil.sensors_temperatures()
        except Exception:
            temperatures = {}
        for sensor, entries in (temperatures or {}).items():
            for entry in entries:
                payload["temperatures"].append(
                    {
                        "sensor": sensor,
                        "label": entry.label or sensor,
                        "current": entry.current,
                        "high": entry.high,
                        "critical": entry.critical,
                    }
                )
        try:
            fans = psutil.sensors_fans()
        except Exception:
            fans = {}
        for sensor, entries in (fans or {}).items():
            for entry in entries:
                payload["fans"].append(
                    {
                        "sensor": sensor,
                        "label": entry.label or sensor,
                        "current": entry.current,
                    }
                )
        try:
            battery = psutil.sensors_battery()
        except Exception:
            battery = None
        if battery:
            payload["battery"] = {
                "percent": battery.percent,
                "secsleft": battery.secsleft,
                "power_plugged": battery.power_plugged,
            }
        return payload

    def _get_process_payload(self, process_limit, process_interval_ms):
        now = time.time()
        ttl = max(process_interval_ms, 1000) / 1000.0
        cached = _PROCESS_CACHE.get("payload")
        if cached and (now - _PROCESS_CACHE.get("timestamp", 0.0)) < ttl:
            return cached

        processes = []
        total = 0
        for proc in psutil.process_iter(
            attrs=["pid", "name", "cpu_percent", "memory_percent", "memory_info"]
        ):
            try:
                info = proc.info
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            total += 1
            mem_info = info.get("memory_info")
            processes.append(
                {
                    "pid": info.get("pid"),
                    "name": info.get("name") or "unknown",
                    "cpu_percent": info.get("cpu_percent") or 0.0,
                    "memory_percent": info.get("memory_percent") or 0.0,
                    "memory_rss": getattr(mem_info, "rss", 0) if mem_info else 0,
                }
            )

        top_cpu = sorted(
            processes, key=lambda item: item["cpu_percent"], reverse=True
        )[:process_limit]
        top_memory = sorted(
            processes, key=lambda item: item["memory_percent"], reverse=True
        )[:process_limit]
        payload = {"top_cpu": top_cpu, "top_memory": top_memory, "total": total}
        _PROCESS_CACHE["timestamp"] = now
        _PROCESS_CACHE["payload"] = payload
        return payload

    def _get_postgres_payload(self, config):
        now = time.time()
        ttl = max(config.get("pg_interval_ms", DEFAULT_PG_INTERVAL_MS), 1000) / 1000.0
        cached = _PG_CACHE.get("payload")
        if cached and (now - _PG_CACHE.get("timestamp", 0.0)) < ttl:
            return cached

        errors = []
        warnings = []
        cr = request.env.cr
        current_db = cr.dbname

        connections = self._safe_fetchone(
            cr,
            """
            SELECT
                count(*) AS total,
                count(*) FILTER (WHERE state = 'active') AS active,
                count(*) FILTER (WHERE state = 'idle') AS idle,
                count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_tx
            FROM pg_stat_activity
            WHERE datname = current_database()
            """,
            errors,
            "connections",
        )
        max_connections = self._safe_fetchone(
            cr,
            "SELECT setting::int FROM pg_settings WHERE name = 'max_connections'",
            errors,
            "max_connections",
        )
        conn_pct = None
        if connections and max_connections:
            try:
                conn_pct = (connections[0] / max_connections[0]) * 100
            except Exception:
                conn_pct = None
        db_size = self._safe_fetchone(
            cr,
            "SELECT pg_database_size(current_database())",
            errors,
            "db_size",
        )
        locks = self._safe_fetchone(
            cr,
            "SELECT count(*) FROM pg_locks WHERE NOT granted",
            errors,
            "locks",
        )
        lock_breakdown = self._safe_fetchall(
            cr,
            """
            SELECT mode, count(*)
            FROM pg_locks
            WHERE NOT granted
            GROUP BY mode
            ORDER BY count(*) DESC
            """,
            errors,
            "lock_breakdown",
        )
        db_stats = self._safe_fetchone(
            cr,
            """
            SELECT
                blks_hit,
                blks_read,
                xact_commit,
                xact_rollback,
                tup_inserted,
                tup_updated,
                tup_deleted
            FROM pg_stat_database
            WHERE datname = current_database()
            """,
            errors,
            "database_stats",
        )
        index_stats = self._safe_fetchone(
            cr,
            """
            SELECT
                sum(idx_blks_hit) AS idx_blks_hit,
                sum(idx_blks_read) AS idx_blks_read
            FROM pg_statio_user_indexes
            """,
            errors,
            "index_stats",
        )
        long_queries = self._safe_fetchall(
            cr,
            """
            SELECT
                pid,
                EXTRACT(EPOCH FROM now() - query_start) AS duration,
                state,
                left(regexp_replace(query, '\\s+', ' ', 'g'), 200) AS query
            FROM pg_stat_activity
            WHERE datname = current_database()
                AND state = 'active'
                AND query_start IS NOT NULL
                AND now() - query_start > interval %s
            ORDER BY duration DESC
            LIMIT 5
            """,
            errors,
            "long_queries",
            (f"{config.get('pg_slow_query_seconds', DEFAULT_PG_SLOW_QUERY_SECONDS)} seconds",),
        )
        blocked_queries = self._safe_fetchall(
            cr,
            """
            SELECT
                pid,
                usename,
                EXTRACT(EPOCH FROM now() - query_start) AS duration,
                array_to_string(pg_blocking_pids(pid), ',') AS blocking_pids,
                left(regexp_replace(query, '\\s+', ' ', 'g'), 200) AS query
            FROM pg_stat_activity
            WHERE datname = current_database()
                AND query_start IS NOT NULL
                AND array_length(pg_blocking_pids(pid), 1) IS NOT NULL
            ORDER BY duration DESC
            LIMIT 5
            """,
            errors,
            "blocked_queries",
        )
        db_overview = self._safe_fetchall(
            cr,
            """
            SELECT
                datname,
                numbackends,
                xact_commit,
                xact_rollback,
                blks_hit,
                blks_read,
                tup_inserted,
                tup_updated,
                tup_deleted,
                deadlocks,
                temp_files,
                temp_bytes,
                blk_read_time,
                blk_write_time
            FROM pg_stat_database
            ORDER BY datname
            """,
            errors,
            "db_overview",
        )
        db_sizes = self._safe_fetchall(
            cr,
            "SELECT datname, pg_database_size(datname) FROM pg_database",
            errors,
            "db_sizes",
        )
        db_sizes_map = {row[0]: row[1] for row in (db_sizes or [])}

        autovacuum = self._safe_fetchall(
            cr,
            """
            SELECT
                relname,
                n_live_tup,
                n_dead_tup,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_all_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY n_dead_tup DESC
            LIMIT 5
            """,
            errors,
            "autovacuum",
        )

        bgwriter = self._safe_fetchone(
            cr,
            """
            SELECT
                checkpoints_timed,
                checkpoints_req,
                checkpoint_write_time,
                checkpoint_sync_time,
                buffers_checkpoint,
                buffers_backend,
                buffers_alloc,
                maxwritten_clean
            FROM pg_stat_bgwriter
            """,
            errors,
            "bgwriter",
        )

        wal_stats = None
        wal_exists = self._safe_fetchone(
            cr,
            "SELECT to_regclass('pg_stat_wal')",
            errors,
            "pg_stat_wal_exists",
        )
        if wal_exists and wal_exists[0]:
            wal_stats = self._safe_fetchone(
                cr,
                """
                SELECT wal_records, wal_fpi, wal_bytes, stats_reset
                FROM pg_stat_wal
                """,
                errors,
                "wal_stats",
            )

        cache_hit = None
        index_hit = None
        if db_stats:
            blks_hit = db_stats[0] or 0
            blks_read = db_stats[1] or 0
            total = blks_hit + blks_read
            cache_hit = (blks_hit / total) * 100 if total else None
        if index_stats:
            idx_hit = index_stats[0] or 0
            idx_read = index_stats[1] or 0
            idx_total = idx_hit + idx_read
            index_hit = (idx_hit / idx_total) * 100 if idx_total else None

        stat_statements = []
        if self._has_pg_stat_statements(cr, warnings):
            statement_columns = self._get_stat_statements_columns(cr)
            if statement_columns:
                total_col = (
                    "total_exec_time"
                    if "total_exec_time" in statement_columns
                    else "total_time"
                )
                mean_col = (
                    "mean_exec_time"
                    if "mean_exec_time" in statement_columns
                    else "mean_time"
                )
                stat_statements = self._safe_fetchall(
                    cr,
                    f"""
                    SELECT
                        calls,
                        {total_col},
                        {mean_col},
                        left(regexp_replace(query, '\\s+', ' ', 'g'), 200) AS query
                    FROM pg_stat_statements
                    WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
                    ORDER BY {total_col} DESC
                    LIMIT 5
                    """,
                    errors,
                    "pg_stat_statements",
                )
        elif self._has_pg_extension(cr, "pg_stat_statements"):
            warnings.append("pg_stat_statements_unavailable")
        else:
            warnings.append("pg_stat_statements_missing")

        db_rows = []
        for row in db_overview or []:
            (
                name,
                numbackends,
                xact_commit,
                xact_rollback,
                blks_hit,
                blks_read,
                tup_inserted,
                tup_updated,
                tup_deleted,
                deadlocks,
                temp_files,
                temp_bytes,
                blk_read_time,
                blk_write_time,
            ) = row
            total = (blks_hit or 0) + (blks_read or 0)
            db_rows.append(
                {
                    "name": name,
                    "connections": numbackends,
                    "size": db_sizes_map.get(name),
                    "cache_hit_ratio": (blks_hit / total) * 100 if total else None,
                    "index_hit_ratio": index_hit if name == current_db else None,
                    "xact_commit": xact_commit,
                    "xact_rollback": xact_rollback,
                    "tup_inserted": tup_inserted,
                    "tup_updated": tup_updated,
                    "tup_deleted": tup_deleted,
                    "deadlocks": deadlocks,
                    "temp_files": temp_files,
                    "temp_bytes": temp_bytes,
                    "blk_read_time": blk_read_time,
                    "blk_write_time": blk_write_time,
                }
            )

        payload = {
            "timestamp": now,
            "config": {
                "interval_ms": config.get("pg_interval_ms", DEFAULT_PG_INTERVAL_MS),
                "history_length": config.get(
                    "pg_history_length", DEFAULT_PG_HISTORY_LENGTH
                ),
                "slow_query_seconds": config.get(
                    "pg_slow_query_seconds", DEFAULT_PG_SLOW_QUERY_SECONDS
                ),
                "alert_cache_hit_min": config.get(
                    "pg_alert_cache_hit_min", DEFAULT_PG_ALERT_CACHE_HIT_MIN
                ),
                "alert_idle_in_tx": config.get(
                    "pg_alert_idle_in_tx", DEFAULT_PG_ALERT_IDLE_IN_TX
                ),
                "alert_locks_waiting": config.get(
                    "pg_alert_locks_waiting", DEFAULT_PG_ALERT_LOCKS_WAITING
                ),
                "alert_conn_pct": config.get(
                    "pg_alert_conn_pct", DEFAULT_PG_ALERT_CONN_PCT
                ),
            },
            "connections": {
                "total": connections[0] if connections else None,
                "active": connections[1] if connections else None,
                "idle": connections[2] if connections else None,
                "idle_in_tx": connections[3] if connections else None,
                "max": max_connections[0] if max_connections else None,
                "pct": conn_pct,
            },
            "db_size": db_size[0] if db_size else None,
            "locks": locks[0] if locks else None,
            "lock_breakdown": [
                {"mode": row[0], "count": row[1]} for row in (lock_breakdown or [])
            ],
            "cache_hit_ratio": cache_hit,
            "index_hit_ratio": index_hit,
            "transactions": {
                "commit": db_stats[2] if db_stats else None,
                "rollback": db_stats[3] if db_stats else None,
            },
            "tuples": {
                "inserted": db_stats[4] if db_stats else None,
                "updated": db_stats[5] if db_stats else None,
                "deleted": db_stats[6] if db_stats else None,
            },
            "long_queries": [
                {
                    "pid": row[0],
                    "duration": row[1],
                    "state": row[2],
                    "query": row[3],
                }
                for row in (long_queries or [])
            ],
            "blocked_queries": [
                {
                    "pid": row[0],
                    "user": row[1],
                    "duration": row[2],
                    "blocking_pids": row[3],
                    "query": row[4],
                }
                for row in (blocked_queries or [])
            ],
            "db_overview": db_rows,
            "autovacuum": [
                {
                    "table": row[0],
                    "live_tup": row[1],
                    "dead_tup": row[2],
                    "last_vacuum": self._format_dt(row[3]),
                    "last_autovacuum": self._format_dt(row[4]),
                    "last_analyze": self._format_dt(row[5]),
                    "last_autoanalyze": self._format_dt(row[6]),
                }
                for row in (autovacuum or [])
            ],
            "bgwriter": {
                "checkpoints_timed": bgwriter[0] if bgwriter else None,
                "checkpoints_req": bgwriter[1] if bgwriter else None,
                "checkpoint_write_time": bgwriter[2] if bgwriter else None,
                "checkpoint_sync_time": bgwriter[3] if bgwriter else None,
                "buffers_checkpoint": bgwriter[4] if bgwriter else None,
                "buffers_backend": bgwriter[5] if bgwriter else None,
                "buffers_alloc": bgwriter[6] if bgwriter else None,
                "maxwritten_clean": bgwriter[7] if bgwriter else None,
            },
            "wal": {
                "records": wal_stats[0] if wal_stats else None,
                "fpi": wal_stats[1] if wal_stats else None,
                "bytes": wal_stats[2] if wal_stats else None,
                "stats_reset": self._format_dt(wal_stats[3]) if wal_stats else None,
            },
            "stat_statements": [
                {
                    "calls": row[0],
                    "total_time": row[1],
                    "mean_time": row[2],
                    "query": row[3],
                }
                for row in (stat_statements or [])
            ],
            "current_db": current_db,
            "warnings": warnings,
            "errors": errors,
        }

        _PG_CACHE["timestamp"] = now
        _PG_CACHE["payload"] = payload
        return payload

    def _get_odoo_payload(self, config):
        now = time.time()
        history_length = config.get(
            "odoo_history_length", DEFAULT_ODOO_HISTORY_LENGTH
        )
        REQUEST_METRICS.set_window(history_length)
        http_metrics = REQUEST_METRICS.snapshot(history_length)

        payload = {
            "timestamp": now,
            "db_name": request.env.cr.dbname,
            "config": {
                "interval_ms": config.get(
                    "odoo_interval_ms", DEFAULT_ODOO_INTERVAL_MS
                ),
                "history_length": history_length,
                "error_window_minutes": config.get(
                    "odoo_error_window_minutes",
                    DEFAULT_ODOO_ERROR_WINDOW_MINUTES,
                ),
                "cron_running_seconds": config.get(
                    "odoo_cron_running_seconds",
                    DEFAULT_ODOO_CRON_RUNNING_SECONDS,
                ),
            },
            "http": http_metrics,
            "workers": self._get_worker_stats(),
            "cron": self._get_cron_stats(config),
            "bus": self._get_bus_stats(),
            "mail": self._get_mail_stats(),
            "filestore": self._get_filestore_stats(),
            "errors": self._get_error_stats(config),
            "cache": self._get_cache_stats(),
            "orm": self._get_orm_stats(),
            "external": self._get_external_stats(),
        }
        return payload

    def _get_odoo_log_payload(self, config, log_lines=None, log_search=None):
        now = time.time()
        return {
            "timestamp": now,
            "db_name": request.env.cr.dbname,
            "config": {
                "interval_ms": config.get(
                    "odoo_interval_ms", DEFAULT_ODOO_INTERVAL_MS
                ),
            },
            "logs": self._get_log_stats(config, log_lines, log_search),
        }

    def _model_exists(self, model_name):
        try:
            return model_name in request.env.registry.models
        except Exception:
            return False

    def _get_worker_stats(self):
        if psutil is None:
            return {"available": False, "processes": []}
        try:
            current = psutil.Process(os.getpid())
        except Exception:
            return {"available": False, "processes": []}

        root = current
        try:
            parent = current.parent()
            if parent and self._is_odoo_process(parent):
                root = parent
        except Exception:
            root = current

        processes = [root] + root.children(recursive=True)
        items = []
        busy = 0
        total_rss = 0
        for proc in processes:
            try:
                if not self._is_odoo_process(proc):
                    continue
                cpu = proc.cpu_percent(interval=None)
                mem = proc.memory_info().rss
                total_rss += mem
                if cpu >= 80:
                    busy += 1
                items.append(
                    {
                        "pid": proc.pid,
                        "name": proc.name(),
                        "cpu_percent": cpu,
                        "memory_rss": mem,
                        "status": proc.status(),
                    }
                )
            except Exception:
                continue

        if not items:
            try:
                cpu = current.cpu_percent(interval=None)
                mem = current.memory_info().rss
                items = [
                    {
                        "pid": current.pid,
                        "name": current.name(),
                        "cpu_percent": cpu,
                        "memory_rss": mem,
                        "status": current.status(),
                    }
                ]
                total_rss = mem
                busy = 1 if cpu >= 80 else 0
            except Exception:
                return {"available": False, "processes": []}

        return {
            "available": True,
            "count": len(items),
            "busy": busy,
            "memory_rss": total_rss,
            "processes": items,
        }

    def _is_odoo_process(self, proc):
        try:
            cmdline = " ".join(proc.cmdline()).lower()
        except Exception:
            cmdline = ""
        return "odoo-bin" in cmdline or "odoo" in cmdline

    def _get_cron_stats(self, config=None):
        if not self._model_exists("ir.cron"):
            return {"available": False}
        cron_model = request.env["ir.cron"].sudo()
        now = fields.Datetime.now()
        total = cron_model.search_count([])
        active = cron_model.search_count([("active", "=", True)])
        overdue = cron_model.search_count(
            [("active", "=", True), ("nextcall", "<", now)]
        )
        failed = cron_model.search_count([("failure_count", ">", 0)])
        failed_jobs = cron_model.search(
            [("failure_count", ">", 0)], order="failure_count desc", limit=5
        )
        running_window = DEFAULT_ODOO_CRON_RUNNING_SECONDS
        if config:
            running_window = config.get(
                "odoo_cron_running_seconds", DEFAULT_ODOO_CRON_RUNNING_SECONDS
            )
        running_since = now - timedelta(seconds=max(running_window or 0, 30))
        progress_model = request.env["ir.cron.progress"].sudo()
        progress_rows = progress_model.search_read(
            [("write_date", ">=", running_since)],
            ["cron_id"],
            order="write_date desc",
        )
        running_ids = {
            row.get("cron_id")[0]
            for row in progress_rows
            if row.get("cron_id")
        }
        active_jobs = cron_model.search_read(
            [("active", "=", True)],
            [
                "name",
                "cron_name",
                "nextcall",
                "lastcall",
                "failure_count",
                "interval_number",
                "interval_type",
                "priority",
            ],
            order="nextcall asc",
        )
        active_list = []
        for row in active_jobs:
            cron_id = row.get("id")
            name = row.get("cron_name") or row.get("name") or f"Cron {cron_id}"
            active_list.append(
                {
                    "id": cron_id,
                    "name": name,
                    "status": "running" if cron_id in running_ids else "idle",
                    "nextcall": self._format_dt(row.get("nextcall")),
                    "lastcall": self._format_dt(row.get("lastcall")),
                    "failure_count": row.get("failure_count") or 0,
                    "interval": f"{row.get('interval_number') or 0} {row.get('interval_type') or ''}",
                    "priority": row.get("priority"),
                }
            )
        return {
            "available": True,
            "total": total,
            "active": active,
            "overdue": overdue,
            "failed": failed,
            "running_count": len(running_ids),
            "active_jobs": active_list,
            "top_failed": [
                {
                    "name": job.cron_name or job.name,
                    "failure_count": job.failure_count,
                    "nextcall": self._format_dt(job.nextcall),
                    "lastcall": self._format_dt(job.lastcall),
                }
                for job in failed_jobs
            ],
        }

    def _get_bus_stats(self):
        if not self._model_exists("bus.bus"):
            return {"available": False}
        bus_model = request.env["bus.bus"].sudo()
        pending = bus_model.search_count([])
        online = None
        if self._model_exists("bus.presence"):
            online = (
                request.env["bus.presence"]
                .sudo()
                .search_count([("status", "=", "online")])
            )
        return {"available": True, "pending": pending, "online": online}

    def _get_mail_stats(self):
        if not self._model_exists("mail.mail"):
            return {"available": False}
        mail_model = request.env["mail.mail"].sudo()
        since = fields.Datetime.now() - timedelta(hours=1)
        outgoing = mail_model.search_count([("state", "=", "outgoing")])
        failed = mail_model.search_count([("state", "=", "exception")])
        sent_recent = mail_model.search_count(
            [("state", "=", "sent"), ("create_date", ">=", since)]
        )
        return {
            "available": True,
            "outgoing": outgoing,
            "failed": failed,
            "sent_recent": sent_recent,
        }

    def _get_filestore_stats(self):
        if not self._model_exists("ir.attachment"):
            return {"available": False}
        attachment_model = request.env["ir.attachment"].sudo()
        store_domain = [("store_fname", "!=", False)]
        data = attachment_model.read_group(store_domain, ["file_size:sum"], [])
        total_size = (data[0].get("file_size_sum") if data else None) or 0
        filestore_count = attachment_model.search_count(store_domain)
        db_count = attachment_model.search_count([("store_fname", "=", False)])
        return {
            "available": True,
            "attachments": filestore_count,
            "db_attachments": db_count,
            "size": total_size or 0,
        }

    def _get_error_stats(self, config):
        if not self._model_exists("ir.logging"):
            return {"available": False, "total": 0, "top": []}
        window = config.get(
            "odoo_error_window_minutes", DEFAULT_ODOO_ERROR_WINDOW_MINUTES
        )
        since = fields.Datetime.now() - timedelta(minutes=window)
        logging_model = request.env["ir.logging"].sudo()
        domain = [
            ("create_date", ">=", since),
            ("level", "in", ("ERROR", "CRITICAL")),
        ]
        total = logging_model.search_count(domain)
        logs = logging_model.search_read(
            domain, ["name"], limit=200, order="create_date desc"
        )
        counts = {}
        for log in logs:
            name = log.get("name") or "Error"
            counts[name] = counts.get(name, 0) + 1
        top = [
            {"name": name, "count": count}
            for name, count in sorted(
                counts.items(), key=lambda item: item[1], reverse=True
            )
        ]
        return {"available": True, "total": total, "top": top[:6]}

    def _get_cache_stats(self):
        registry = request.env.registry
        caches = getattr(registry, "_Registry__caches", None)
        if not caches:
            return {"available": False}
        entries = []
        total_entries = 0
        for name, cache in caches.items():
            try:
                size = len(cache)
            except Exception:
                size = None
            if size is None:
                continue
            entries.append({"name": name, "entries": size})
            total_entries += size
        entries.sort(key=lambda row: row["entries"], reverse=True)
        return {
            "available": True,
            "count": len(caches),
            "entries": total_entries,
            "largest": entries[:5],
        }

    def _get_orm_stats(self):
        cr = request.env.cr
        if not self._has_pg_stat_statements(cr):
            return {"available": False, "statements": []}
        statement_columns = self._get_stat_statements_columns(cr)
        if not statement_columns:
            return {"available": False, "statements": []}
        total_col = (
            "total_exec_time"
            if "total_exec_time" in statement_columns
            else "total_time"
        )
        mean_col = (
            "mean_exec_time" if "mean_exec_time" in statement_columns else "mean_time"
        )
        rows = self._safe_fetchall(
            cr,
            f"""
            SELECT
                calls,
                {total_col},
                {mean_col},
                left(regexp_replace(query, '\\s+', ' ', 'g'), 200) AS query
            FROM pg_stat_statements
            WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
            ORDER BY {total_col} DESC
            LIMIT 5
            """,
            [],
            "odoo_pg_stat_statements",
        )
        statements = [
            {
                "calls": row[0],
                "total_time": row[1],
                "mean_time": row[2],
                "query": row[3],
            }
            for row in (rows or [])
        ]
        return {"available": True, "statements": statements}

    def _get_external_stats(self):
        mail_servers = None
        if self._model_exists("ir.mail_server"):
            mail_servers = request.env["ir.mail_server"].sudo().search_count([])
        payment_providers = None
        if self._model_exists("payment.provider"):
            payment_providers = (
                request.env["payment.provider"]
                .sudo()
                .search_count([("state", "in", ("enabled", "test"))])
            )
        attachment_location = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("ir_attachment.location")
        )
        return {
            "mail_servers": mail_servers,
            "payment_providers": payment_providers,
            "attachment_location": attachment_location or "filestore",
        }

    def _get_log_stats(self, config, log_lines=None, log_search=None):
        icp = request.env["ir.config_parameter"].sudo()
        logfile = icp.get_param("server_monitor.logfile") or odoo_config.get(
            "logfile"
        )
        if not logfile:
            return {"available": False, "message": "logfile_not_configured"}
        if not os.path.isfile(logfile):
            return {
                "available": False,
                "message": "logfile_missing",
                "path": logfile,
            }
        line_count = (
            self._parse_int_safe(log_lines)
            if log_lines is not None
            else config.get("odoo_log_lines", DEFAULT_ODOO_LOG_LINES)
        )
        line_count = max(min(line_count or 0, 2000), 20)
        lines = self._tail_file_lines(logfile, line_count)
        search = (log_search or "").strip()
        if search:
            lowered = search.lower()
            lines = [line for line in lines if lowered in line.lower()]
        return {
            "available": True,
            "path": logfile,
            "lines": lines,
            "search": search,
        }

    def _parse_int_safe(self, value):
        try:
            return int(value)
        except Exception:
            return None

    def _tail_file_lines(self, path, line_count):
        if not line_count or line_count <= 0:
            return []
        try:
            with open(path, "rb") as handle:
                handle.seek(0, os.SEEK_END)
                file_size = handle.tell()
                chunk_size = 4096
                buffer = b""
                position = file_size
                while position > 0 and buffer.count(b"\n") <= line_count:
                    read_size = min(chunk_size, position)
                    position -= read_size
                    handle.seek(position)
                    buffer = handle.read(read_size) + buffer
                    if len(buffer) > 5 * 1024 * 1024:
                        break
                lines = buffer.splitlines()[-line_count:]
                return [
                    line.decode("utf-8", errors="ignore") for line in lines
                ]
        except Exception:
            return []

    def _safe_fetchone(self, cr, query, errors, label, params=None):
        try:
            cr.execute(query, params or ())
            return cr.fetchone()
        except Exception:
            errors.append(label)
            return None

    def _safe_fetchall(self, cr, query, errors, label, params=None):
        try:
            cr.execute(query, params or ())
            return cr.fetchall()
        except Exception:
            errors.append(label)
            return []

    def _has_pg_extension(self, cr, name):
        try:
            cr.execute("SELECT 1 FROM pg_extension WHERE extname = %s", (name,))
            return cr.fetchone() is not None
        except Exception:
            return False

    def _has_pg_stat_statements(self, cr, warnings=None):
        if not self._has_pg_extension(cr, "pg_stat_statements"):
            return False
        if not self._is_pg_stat_statements_preloaded(cr):
            if warnings is not None:
                warnings.append("pg_stat_statements_unavailable")
            return False
        try:
            cr.execute("SELECT 1 FROM pg_stat_statements LIMIT 1")
            cr.fetchone()
            return True
        except Exception:
            if warnings is not None:
                warnings.append("pg_stat_statements_unavailable")
            return False

    def _is_pg_stat_statements_preloaded(self, cr):
        try:
            cr.execute(
                "SELECT setting FROM pg_settings WHERE name = 'shared_preload_libraries'"
            )
            row = cr.fetchone()
        except Exception:
            return False
        if not row:
            return False
        setting = row[0] or ""
        return "pg_stat_statements" in [item.strip() for item in setting.split(",")]

    def _get_stat_statements_columns(self, cr):
        try:
            cr.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pg_stat_statements'
                """
            )
            return {row[0] for row in cr.fetchall()}
        except Exception:
            return set()

    def _format_dt(self, value):
        if not value:
            return None
        try:
            return value.isoformat()
        except Exception:
            return str(value)

    def _apply_network_rates(self, payload):
        user_key = request.env.user.id
        previous = _USER_NET_STATE.get(user_key, {"timestamp": None, "counters": {}})
        prev_timestamp = previous["timestamp"]
        current_timestamp = payload["timestamp"]
        delta = (
            max(current_timestamp - prev_timestamp, 0.001)
            if prev_timestamp
            else 1.0
        )

        counters = {}
        for adapter in payload["network"]:
            name = adapter["name"]
            prev_counters = previous["counters"].get(name)
            if prev_counters:
                in_bytes = max(adapter["bytes_recv"] - prev_counters["bytes_recv"], 0)
                out_bytes = max(
                    adapter["bytes_sent"] - prev_counters["bytes_sent"], 0
                )
                adapter["in_mbits"] = (in_bytes * 8) / (delta * 1024 * 1024)
                adapter["out_mbits"] = (out_bytes * 8) / (delta * 1024 * 1024)
            else:
                adapter["in_mbits"] = 0.0
                adapter["out_mbits"] = 0.0
            counters[name] = {
                "bytes_sent": adapter["bytes_sent"],
                "bytes_recv": adapter["bytes_recv"],
            }

        _USER_NET_STATE[user_key] = {
            "timestamp": current_timestamp,
            "counters": counters,
        }

    def _apply_disk_rates(self, payload):
        user_key = request.env.user.id
        previous = _USER_DISK_STATE.get(user_key, {"timestamp": None, "counters": {}})
        prev_timestamp = previous["timestamp"]
        current_timestamp = payload["timestamp"]
        delta = (
            max(current_timestamp - prev_timestamp, 0.001)
            if prev_timestamp
            else 1.0
        )

        counters = {}
        for disk in payload.get("disk_io", []):
            name = disk.get("name", "disk")
            prev_counters = previous["counters"].get(name)
            if prev_counters:
                read_bytes = max(
                    disk.get("read_bytes", 0) - prev_counters.get("read_bytes", 0),
                    0,
                )
                write_bytes = max(
                    disk.get("write_bytes", 0)
                    - prev_counters.get("write_bytes", 0),
                    0,
                )
                disk["read_mbs"] = read_bytes / (delta * 1024 * 1024)
                disk["write_mbs"] = write_bytes / (delta * 1024 * 1024)
            else:
                disk["read_mbs"] = 0.0
                disk["write_mbs"] = 0.0
            counters[name] = {
                "read_bytes": disk.get("read_bytes", 0),
                "write_bytes": disk.get("write_bytes", 0),
            }

        _USER_DISK_STATE[user_key] = {
            "timestamp": current_timestamp,
            "counters": counters,
        }

    def _get_gpu_payload(self, gpu_interval_ms):
        now = time.time()
        ttl = max(gpu_interval_ms, 1000) / 1000.0
        cached = _GPU_CACHE.get("payload")
        if cached and (now - _GPU_CACHE.get("timestamp", 0.0)) < ttl:
            return cached

        gpus = []
        gpus.extend(self._get_nvidia_gpus())
        gpus.extend(self._get_amd_gpus())
        gpus.extend(self._get_intel_gpus())
        vendors = {gpu.get("vendor") for gpu in gpus if gpu.get("vendor")}
        sysfs_gpus = self._get_sysfs_gpus()
        if vendors:
            sysfs_gpus = [
                gpu for gpu in sysfs_gpus if gpu.get("vendor") not in vendors
            ]
        gpus.extend(sysfs_gpus)
        if os.name == "nt":
            gpus = self._merge_gpu_entries(gpus, self._get_windows_gpu_names())

        deduped = {}
        for gpu in gpus:
            gpu_id = gpu.get("id") or gpu.get("name")
            if not gpu_id:
                continue
            if gpu_id not in deduped:
                deduped[gpu_id] = gpu
                continue
            existing = deduped[gpu_id]
            for key, value in gpu.items():
                if existing.get(key) in (None, "", 0) and value not in (None, "", 0):
                    existing[key] = value

        result = list(deduped.values())
        _GPU_CACHE["timestamp"] = now
        _GPU_CACHE["payload"] = result
        return result

    def _get_nvidia_gpus(self):
        gpus = self._get_nvidia_gpus_nvml()
        if gpus:
            return gpus
        return self._get_nvidia_gpus_smi()

    def _get_nvidia_gpus_nvml(self):
        try:
            import pynvml  # type: ignore
        except Exception:
            return []

        gpus = []
        try:
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            for index in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(index)
                name = pynvml.nvmlDeviceGetName(handle)
                uuid = pynvml.nvmlDeviceGetUUID(handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                temperature = None
                fan_speed = None
                power_draw = None
                clock_sm = None
                clock_mem = None
                try:
                    temperature = pynvml.nvmlDeviceGetTemperature(
                        handle, pynvml.NVML_TEMPERATURE_GPU
                    )
                except Exception:
                    temperature = None
                try:
                    fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
                except Exception:
                    fan_speed = None
                try:
                    power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                except Exception:
                    power_draw = None
                try:
                    clock_sm = pynvml.nvmlDeviceGetClockInfo(
                        handle, pynvml.NVML_CLOCK_GRAPHICS
                    )
                except Exception:
                    clock_sm = None
                try:
                    clock_mem = pynvml.nvmlDeviceGetClockInfo(
                        handle, pynvml.NVML_CLOCK_MEM
                    )
                except Exception:
                    clock_mem = None

                gpus.append(
                    self._normalize_gpu(
                        gpu_id=uuid.decode() if isinstance(uuid, bytes) else str(uuid),
                        name=name.decode() if isinstance(name, bytes) else str(name),
                        vendor="nvidia",
                        utilization=utilization.gpu if utilization else None,
                        memory_total=memory.total if memory else None,
                        memory_used=memory.used if memory else None,
                        temperature=temperature,
                        fan_speed=fan_speed,
                        power_draw=power_draw,
                        clock_sm=clock_sm,
                        clock_mem=clock_mem,
                        index=index,
                    )
                )
        except Exception:
            return []
        finally:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
        return gpus

    def _get_nvidia_gpus_smi(self):
        if not shutil.which("nvidia-smi"):
            return []
        fields = [
            "index",
            "uuid",
            "name",
            "utilization.gpu",
            "memory.total",
            "memory.used",
            "temperature.gpu",
            "fan.speed",
            "power.draw",
            "clocks.sm",
            "clocks.mem",
        ]
        command = [
            "nvidia-smi",
            f"--query-gpu={','.join(fields)}",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=1.5,
            )
        except Exception:
            return []
        if result.returncode != 0:
            return []
        gpus = []
        for line in result.stdout.splitlines():
            parts = [item.strip() for item in line.split(",")]
            if len(parts) < len(fields):
                continue
            data = dict(zip(fields, parts))
            memory_total = self._parse_float(data.get("memory.total"))
            memory_used = self._parse_float(data.get("memory.used"))
            gpus.append(
                self._normalize_gpu(
                    gpu_id=data.get("uuid") or data.get("index"),
                    name=data.get("name") or "NVIDIA GPU",
                    vendor="nvidia",
                    utilization=self._parse_float(data.get("utilization.gpu")),
                    memory_total=self._mb_to_bytes(memory_total),
                    memory_used=self._mb_to_bytes(memory_used),
                    temperature=self._parse_float(data.get("temperature.gpu")),
                    fan_speed=self._parse_float(data.get("fan.speed")),
                    power_draw=self._parse_float(data.get("power.draw")),
                    clock_sm=self._parse_float(data.get("clocks.sm")),
                    clock_mem=self._parse_float(data.get("clocks.mem")),
                    index=self._parse_int_safe(data.get("index")),
                )
            )
        return gpus

    def _get_amd_gpus(self):
        if not shutil.which("rocm-smi"):
            return []
        command = [
            "rocm-smi",
            "--showuse",
            "--showmemuse",
            "--showtemp",
            "--showfan",
            "--showpower",
            "--showproductname",
            "--showclocks",
            "--showmeminfo",
            "vram",
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=1.5,
            )
        except Exception:
            return []
        if result.returncode != 0:
            return []

        gpu_data = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line.startswith("GPU["):
                continue
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            gpu_index = parts[0].strip()
            key = gpu_index.replace("GPU[", "").replace("]", "").strip()
            metric = parts[1].strip()
            value = parts[2].strip()
            entry = gpu_data.setdefault(key, {})
            if "Product Name" in metric or "Card series" in metric:
                entry["name"] = value
            elif "GPU use" in metric:
                entry["utilization"] = self._parse_float(value)
            elif "VRAM use" in metric:
                entry["memory_percent"] = self._parse_float(value)
            elif "VRAM Total" in metric:
                entry["memory_total"] = self._parse_float(value)
            elif "VRAM Used" in metric:
                entry["memory_used"] = self._parse_float(value)
            elif "Temperature" in metric:
                entry["temperature"] = self._parse_float(value)
            elif "Fan Speed" in metric:
                entry["fan_speed"] = self._parse_float(value)
            elif "Average Graphics Package Power" in metric or "Power" in metric:
                entry["power_draw"] = self._parse_float(value)
            elif "SCLK" in metric:
                entry["clock_sm"] = self._parse_float(value)
            elif "MCLK" in metric:
                entry["clock_mem"] = self._parse_float(value)

        gpus = []
        for index, data in gpu_data.items():
            memory_total = data.get("memory_total")
            memory_used = data.get("memory_used")
            gpus.append(
                self._normalize_gpu(
                    gpu_id=f"amd-{index}",
                    name=data.get("name") or f"AMD GPU {index}",
                    vendor="amd",
                    utilization=data.get("utilization"),
                    memory_total=self._bytes_from_maybe_bytes(memory_total),
                    memory_used=self._bytes_from_maybe_bytes(memory_used),
                    memory_percent=data.get("memory_percent"),
                    temperature=data.get("temperature"),
                    fan_speed=data.get("fan_speed"),
                    power_draw=data.get("power_draw"),
                    clock_sm=data.get("clock_sm"),
                    clock_mem=data.get("clock_mem"),
                    index=self._parse_int_safe(index),
                )
            )
        return gpus

    def _get_sysfs_gpus(self):
        sysfs_root = "/sys/class/drm"
        if not os.path.isdir(sysfs_root):
            return []
        gpus = []
        for name in os.listdir(sysfs_root):
            if not name.startswith("card"):
                continue
            device_dir = os.path.join(sysfs_root, name, "device")
            busy_path = os.path.join(device_dir, "gpu_busy_percent")
            if not os.path.isfile(busy_path):
                continue
            utilization = self._read_int_file(busy_path)
            vendor_id = self._read_hex_file(os.path.join(device_dir, "vendor"))
            vendor = self._vendor_from_id(vendor_id)
            mem_total = self._read_int_file(
                os.path.join(device_dir, "mem_info_vram_total")
            )
            mem_used = self._read_int_file(
                os.path.join(device_dir, "mem_info_vram_used")
            )
            gpus.append(
                self._normalize_gpu(
                    gpu_id=f"sysfs-{name}",
                    name=f"{vendor} {name}".strip(),
                    vendor=vendor.lower(),
                    utilization=utilization,
                    memory_total=mem_total if mem_total else None,
                    memory_used=mem_used if mem_used else None,
                    index=self._parse_int_safe(name.replace("card", "")),
                )
            )
        return gpus

    def _get_intel_gpus(self):
        if not shutil.which("intel_gpu_top"):
            return []
        command = ["intel_gpu_top", "-J", "-s", "1000", "-o", "-"]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=1.5,
            )
        except Exception:
            return []
        if result.returncode != 0:
            return []
        try:
            payload = json.loads(result.stdout.splitlines()[-1])
        except Exception:
            return []
        engines = payload.get("engines", {})
        render = engines.get("Render/3D") or engines.get("Render") or {}
        utilization = render.get("busy") or render.get("busy_percent")
        gpus = [
            self._normalize_gpu(
                gpu_id="intel-0",
                name=payload.get("device", "Intel GPU"),
                vendor="intel",
                utilization=utilization,
                index=0,
            )
        ]
        return gpus

    def _get_windows_gpu_names(self):
        if os.name != "nt":
            return []
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name,AdapterRAM,PNPDeviceID | ConvertTo-Json -Compress",
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=2.0,
            )
        except Exception:
            return []
        if result.returncode != 0 or not result.stdout.strip():
            return []
        try:
            data = json.loads(result.stdout)
        except Exception:
            return []
        entries = data if isinstance(data, list) else [data]
        gpus = []
        for index, entry in enumerate(entries):
            name = entry.get("Name") or f"GPU {index}"
            adapter_ram = entry.get("AdapterRAM")
            gpus.append(
                self._normalize_gpu(
                    gpu_id=entry.get("PNPDeviceID") or f"win-{index}",
                    name=name,
                    vendor=self._guess_vendor(name),
                    memory_total=adapter_ram,
                    index=index,
                )
            )
        return gpus

    def _merge_gpu_entries(self, primary, secondary):
        merged = {gpu.get("id"): gpu for gpu in primary if gpu.get("id")}
        for gpu in secondary:
            gpu_id = gpu.get("id")
            if not gpu_id:
                continue
            if gpu_id not in merged:
                merged[gpu_id] = gpu
                continue
            existing = merged[gpu_id]
            for key, value in gpu.items():
                if existing.get(key) in (None, "", 0) and value not in (None, "", 0):
                    existing[key] = value
        return list(merged.values())

    def _normalize_gpu(
        self,
        gpu_id,
        name,
        vendor,
        utilization=None,
        memory_total=None,
        memory_used=None,
        memory_percent=None,
        temperature=None,
        fan_speed=None,
        power_draw=None,
        clock_sm=None,
        clock_mem=None,
        index=None,
    ):
        if memory_percent is None and memory_total and memory_used is not None:
            try:
                memory_percent = (memory_used / memory_total) * 100.0
            except Exception:
                memory_percent = None
        memory_free = None
        if memory_total is not None and memory_used is not None:
            memory_free = max(memory_total - memory_used, 0)
        return {
            "id": str(gpu_id),
            "index": index,
            "name": name,
            "vendor": vendor,
            "utilization": self._parse_float(utilization),
            "memory_total": self._parse_float(memory_total),
            "memory_used": self._parse_float(memory_used),
            "memory_free": self._parse_float(memory_free),
            "memory_percent": self._parse_float(memory_percent),
            "temperature": self._parse_float(temperature),
            "fan_speed": self._parse_float(fan_speed),
            "power_draw": self._parse_float(power_draw),
            "clock_sm": self._parse_float(clock_sm),
            "clock_mem": self._parse_float(clock_mem),
        }

    def _parse_float(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        cleaned = (
            str(value)
            .replace("%", "")
            .replace("C", "")
            .replace("c", "")
            .replace("W", "")
            .replace("w", "")
            .replace("MHz", "")
            .replace("Mhz", "")
            .replace("mhz", "")
            .replace("MiB", "")
            .replace("MB", "")
            .replace("B", "")
            .replace(",", "")
        )
        try:
            return float(cleaned.strip())
        except Exception:
            return None

    def _parse_int_safe(self, value):
        try:
            return int(value)
        except Exception:
            return None

    def _mb_to_bytes(self, value):
        if value is None:
            return None
        return value * 1024 * 1024

    def _bytes_from_maybe_bytes(self, value):
        if value is None:
            return None
        if value > 1024 * 1024 * 1024:
            return value
        return value * 1024 * 1024

    def _read_int_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return int(handle.read().strip())
        except Exception:
            return None

    def _read_hex_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return int(handle.read().strip(), 16)
        except Exception:
            return None

    def _vendor_from_id(self, vendor_id):
        if vendor_id == 0x10DE:
            return "NVIDIA"
        if vendor_id == 0x1002:
            return "AMD"
        if vendor_id == 0x8086:
            return "Intel"
        return "GPU"

    def _guess_vendor(self, name):
        lowered = (name or "").lower()
        if "nvidia" in lowered:
            return "nvidia"
        if "amd" in lowered or "radeon" in lowered:
            return "amd"
        if "intel" in lowered:
            return "intel"
        return "gpu"
