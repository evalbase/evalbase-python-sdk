# telemetry.py
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import set_meter_provider, get_meter_provider

# Globals for easy access
tracer = None
meter = None
function_call_counter = None

def configure_telemetry(service_name=None, endpoint=None, api_key=None):
    global tracer, meter, function_call_counter

    default_endpoint = "https://otel-http.staging.evalbase.ai"
    endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", default_endpoint)
    endpoint = endpoint.rstrip('/')

    headers = {}
    api_key = api_key or os.getenv("EVALBASE_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    resource_attrs = {
        "service.name": service_name or os.getenv("OTEL_SERVICE_NAME", "evalbase-ai-agent")
    }
    resource = Resource(attributes=resource_attrs)

    # Tracer Setup
    trace_endpoint = f"{endpoint}/v1/traces"
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(endpoint=trace_endpoint, headers=headers)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
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
        unit="1"
    )
