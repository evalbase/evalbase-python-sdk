# Evalbase

Evalbase is a lightweight, easy-to-use Python SDK for instrumenting AI workflows with OpenTelemetry.

## Installation

To install Evalbase from PyPI, run:

```bash
pip install evalbase
```

To install from source, clone this repository and run:

```bash
git clone https://github.com/evalbase/evalbase-python-sdk.git
cd evalbase-python-sdk
pip install .
```

## Usage

1. **Configuration**: You can configure telemetry for your AI application by calling `configure_telemetry`. 

```python
from evalbase import configure_telemetry

configure_telemetry(
    service_name="my-ai-service",
    endpoint="https://otel-http.staging.evalbase.ai",  # Optional override
    api_key="apikey-123"  # Or set EVALBASE_API_KEY in your environment
)
```

2. **Workflow and Step Decorators**: Mark your functions with `@workflow` or `@step(...)` to automatically collect tracing and metrics.

```python
from evalbase import workflow, step, StepType

@workflow
def my_workflow():
    result = my_llm_step("example")
    return result

@step(type=StepType.LLM)
def my_llm_step(prompt):
    # Your LLM logic here
    return "some LLM response"
```

3. **Example**: For a complete example of how to implement and test a workflow with steps, see the `integration_tests` directory.

```bash
python -m integration_tests.test_live_telemetry
```

For more information, check out the source code in `decorators.py`, `telemetry.py`, and `integration_tests/test_live_telemetry.py`.
