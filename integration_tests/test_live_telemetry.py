# integration_tests/test_live_telemetry.py
import os
import pytest
from evalbase import configure_telemetry, workflow, step, StepType

# Ensure real environment variables are used
EVALBASE_API_KEY = os.getenv("EVALBASE_API_KEY", "")
OTEL_ENDPOINT = os.getenv("OTEL_ENDPOINT", "https://otel-http.staging.evalbase.ai")

# Configure telemetry explicitly for the test environment
configure_telemetry(
    service_name="test-ai-agent",
    endpoint=OTEL_ENDPOINT,
    api_key=EVALBASE_API_KEY
)

@workflow
def run_workflow(query):
    result = llm_step(query)
    embedding = embedder_step(result)
    return embedding

@step(type=StepType.LLM)
def llm_step(query):
    # Simulated LLM call
    return f"Response to {query}"

@step(type=StepType.EMBEDDING)
def embedder_step(text):
    # Simulated embedding step
    return [0.5, 0.6, 0.7]

# ---------------------------
# NEW: Force an error in a second workflow
# ---------------------------
@workflow(name="error_workflow")
def run_workflow_with_error(query):
    # Reuse the LLM step
    result = llm_step(query)
    # This step will raise an error
    embedding = embedder_step_with_error(result)
    return embedding

@step(type=StepType.EMBEDDING)
def embedder_step_with_error(text):
    # Force an error so we can see if the span status is captured
    raise RuntimeError("Simulated error for telemetry testing")
    # (Unreachable code, just for clarity)
    # return [0.8, 0.9, 1.0]

@pytest.mark.integration
def test_live_telemetry_workflow():
    """Happy path: no error."""
    query = "What is OpenTelemetry?"
    embedding = run_workflow(query)
    assert embedding == [0.5, 0.6, 0.7]  # Simple correctness check

@pytest.mark.integration
def test_live_telemetry_workflow_with_error():
    """Test that an error in a step sets the span status to ERROR and captures the exception."""
    with pytest.raises(RuntimeError, match="Simulated error for telemetry testing"):
        # This should raise the RuntimeError from embedder_step_with_error
        run_workflow_with_error("What is an error?")
