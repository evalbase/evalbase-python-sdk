import os
import pytest
import base64
from evalbase import configure_telemetry, workflow, step, StepType

# Ensure real environment variables are used
EVALBASE_API_KEY = os.getenv("EVALBASE_API_KEY", "")
# If running tests against local kind cluster, export the certificate and set env vars to use it:
# kubectl get secret ingress-cert-secret -n istio-system -o jsonpath='{.data.ca\.crt}' | base64 --decode > ca.crt
# OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=ca.crt
# OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE=ca.crt
# OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE=ca.crt
OTEL_ENDPOINT = os.getenv("OTEL_ENDPOINT", "https://otel-http.staging.evalbase.ai")
os.environ["OTEL_EXPORTER_OTLP_TRACES_TIMEOUT"] = "180"

# Configure telemetry explicitly for the test environment
configure_telemetry(
    service_name="test-ai-agent",
    endpoint=OTEL_ENDPOINT,
    api_key=EVALBASE_API_KEY,
    loki_enabled=True,
)


def _load_file(filename: str) -> bytes:
    # Get current working directory
    cwd = os.getcwd()
    # If running in the same folder as this file, use the relative path
    if cwd != os.path.dirname(os.path.abspath(__file__)):
        filename = f"{cwd}/performance_tests/{filename}"
    with open(filename, "rb") as f:
        return f.read()


@step(type=StepType.LLM)
def large_llm_step(query: str, reference_file: bytes):
    # Simulated LLM call with a large response
    encoded_bytes = base64.b64encode(reference_file)
    return f"Response to {query}: {encoded_bytes.decode('utf-8')}"


@workflow(name="large I/O workflow")
def run_workflow_with_large_io(query: str, reference_file: bytes):
    for _ in range(39):
        large_llm_step(query, reference_file)
    result = large_llm_step(query, reference_file)
    return result


@pytest.mark.integration
def test_live_telemetry_workflow_with_large_io():
    """Tests that large function arguments and responses are handled correctly."""
    file_contents = _load_file("OracleInstallGuide.pdf")
    reponse = run_workflow_with_large_io("Explain how to install Oracle", file_contents)
    assert "Response to Explain how to install Oracle" in reponse
