"""Prometheus metrics for monitoring error gateway."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Counters
ERROR_TOTAL = Counter(
    "error_gateway_errors_total",
    "Total number of errors processed",
    ["exception_type", "environment", "release_version"],
)

ERROR_PROCESSED = Counter(
    "error_gateway_errors_processed_total",
    "Total number of errors successfully processed",
    ["exception_type"],
)

NOTIFICATION_SENT = Counter(
    "error_gateway_notifications_sent_total",
    "Total number of notifications sent",
    ["channel", "status"],
)

NOTIFICATION_FAILED = Counter(
    "error_gateway_notifications_failed_total",
    "Total number of notification failures",
    ["channel", "exception_type"],
)

REQUEST_TOTAL = Counter(
    "error_gateway_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status_code"],
)

# Gauges
ERROR_GROUPS_TOTAL = Gauge(
    "error_gateway_error_groups_total",
    "Total number of unique error groups",
)

ACTIVE_CHANNELS = Gauge(
    "error_gateway_active_channels",
    "Number of active notification channels",
    ["channel"],
)

# Histograms
REQUEST_LATENCY = Histogram(
    "error_gateway_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ERROR_PROCESSING_TIME = Histogram(
    "error_gateway_processing_time_seconds",
    "Time spent processing errors",
    ["exception_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)


def generate_metrics() -> bytes:
    """Generate Prometheus metrics in text format."""
    return generate_latest()
