# telemetry.py
import os
import time
from typing import Optional
import logging

from opentelemetry import _logs as otel_logs_api
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.metrics import Counter, Meter, get_meter_provider, set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider, LogRecord
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Globals for easy access
tracer: Optional[trace.Tracer] = None
meter: Optional[Meter] = None
otel_logger: Optional[otel_logs_api.Logger] = None
logger_provider: Optional[LoggerProvider] = None
function_call_counter: Optional[Counter] = None
is_loki_enabled: bool = False

_logger = logging.getLogger(__name__)


def configure_telemetry(
    service_name: Optional[str] = None,
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    loki_enabled: bool = True,
):
    """
    Configures the telemetry setup for the evalbase Python SDK.

    Args:
        service_name: The name of the service. If not provided, takes the value of the environment variable "OTEL_SERVICE_NAME". Defaults to "evalbase-ai-agent".
        endpoint: The endpoint to send telemetry data to. If not provided, takes the value of the environment variable "OTEL_EXPORTER_OTLP_ENDPOINT". Defaults to "https://otel-http.staging.evalbase.ai".
        api_key: The API key for authentication. If not provided, takes the value of the environment variable "EVALBASE_API_KEY".
        loki_enabled: Whether expected function arguments and/or responses are stored in loki.
    """
    global \
        tracer, \
        meter, \
        function_call_counter, \
        otel_logger, \
        logger_provider, \
        is_loki_enabled

    default_endpoint = "https://otel-http.staging.evalbase.ai"
    endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", default_endpoint)
    endpoint = endpoint.rstrip("/")

    headers = {}
    api_key = api_key or os.getenv("EVALBASE_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "evalbase-ai-agent")

    _logger.debug(
        "Configuring telemetry for service %s, endpoint %s, loki enabled: %s",
        service_name,
        endpoint,
        loki_enabled,
    )

    resource_attrs = {"service.name": service_name}
    resource = Resource(attributes=resource_attrs)

    # Tracer Setup
    trace_endpoint = f"{endpoint}/v1/traces"
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(endpoint=trace_endpoint, headers=headers)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter, max_export_batch_size=10))
    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer(resource_attrs["service.name"])

    # Metrics Setup
    metrics_endpoint = f"{endpoint}/v1/metrics"
    metric_exporter = OTLPMetricExporter(endpoint=metrics_endpoint, headers=headers)
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    set_meter_provider(meter_provider)
    meter = get_meter_provider().get_meter(resource_attrs["service.name"])

    function_call_counter = meter.create_counter(
        name="evalbase.function.calls",
        description="Counts function calls for evalbase telemetry decorators",
        unit="1",
    )

    # Logging Setup
    is_loki_enabled = loki_enabled
    if is_loki_enabled:
        logs_endpoint = f"{endpoint}/v1/logs"
        logger_provider = LoggerProvider(resource=resource)
        log_exporter = OTLPLogExporter(logs_endpoint, headers=headers)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(log_exporter, max_export_batch_size=10)
        )
        otel_logs_api.set_logger_provider(logger_provider)
        otel_logger = otel_logs_api.get_logger_provider().get_logger(
            resource_attrs["service.name"],
        )


def record_function_data(
    func_args: str, func_kwargs: str, func_result: str, span: trace.Span
) -> None:
    """
    Records the function arguments, keyword arguments, and result of a function execution in the provided span.

    Args:
        func_args: The function arguments.
        func_kwargs: The function keyword arguments.
        func_result: The function result.
        span: The current span context.
    """
    _logger.debug(
        "Recording function data in span: %s, is loki enabled: %s",
        span,
        is_loki_enabled,
    )

    # Store everything in span attributes
    span.set_attribute("function.args", func_args)
    span.set_attribute("function.kwargs", func_kwargs)
    span.set_attribute("function.return", func_result)

    if not is_loki_enabled:
        return

    global otel_logger, logger_provider

    if otel_logger is None or logger_provider is None:
        _logger.warning(
            "Warning: Evalbase Telemetry Logger not configured. Call configure_telemetry(loki_enabled=True) first."
        )
        return

    span_context = span.get_span_context()
    current_timestamp_ns = time.time_ns()

    otel_logger.emit(
        _build_log_record(
            current_timestamp_ns,
            span_context,
            "function.args",
            func_args,
            logger_provider.resource,
        )
    )
    otel_logger.emit(
        _build_log_record(
            current_timestamp_ns,
            span_context,
            "function.kwargs",
            func_kwargs,
            logger_provider.resource,
        )
    )
    otel_logger.emit(
        _build_log_record(
            current_timestamp_ns,
            span_context,
            "function.return",
            func_result,
            logger_provider.resource,
        )
    )


def _build_log_record(
    current_timestamp_ns: int,
    span_context: trace.SpanContext,
    attr_name: str,
    attr_value: str,
    resource: Resource,
) -> LogRecord:
    return LogRecord(
        timestamp=current_timestamp_ns,
        observed_timestamp=current_timestamp_ns,
        trace_id=span_context.trace_id,
        span_id=span_context.span_id,
        severity_text="INFO",
        severity_number=otel_logs_api.SeverityNumber.INFO,
        body=attr_value,
        resource=resource,
        trace_flags=trace.DEFAULT_TRACE_OPTIONS,
        attributes={
            "record_type": attr_name,
        },
    )
