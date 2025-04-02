import pytest
from evalbase import workflow, step

@workflow
def example_workflow(a, b):
    return step_function(a) + step_function(b)

@step(subtype="Tool")
def step_function(x):
    return x * 2

def test_workflow():
    assert example_workflow(2, 3) == 10

