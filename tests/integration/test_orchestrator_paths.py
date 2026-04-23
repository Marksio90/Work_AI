import asyncio

from packages.contracts.execution_policy import ExecutionPolicy, RetryPolicy, TimeoutPolicy
from packages.contracts.task_contract import TaskContract
from packages.orchestrator.task_orchestrator import TaskOrchestrator
from packages.providers.mock_provider import MockProvider


class FlakyProvider(MockProvider):
    def __init__(self, fail_times: int):
        super().__init__()
        self.fail_times = fail_times
        self.calls = 0

    async def generate_structured(self, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("temporary provider failure")
        return {"answer": "ok"}


class SlowProvider(MockProvider):
    async def generate_structured(self, **kwargs):
        await asyncio.sleep(0.05)
        return {"answer": "slow"}


class ErrorProvider(MockProvider):
    async def generate_structured(self, **kwargs):
        raise RuntimeError("provider down")


def _contract(policy: ExecutionPolicy | None = None, abstain: bool = False):
    output_schema = {} if abstain else {
        "type": "object",
        "required": ["answer"],
        "properties": {"answer": {"type": "string"}},
        "additionalProperties": True,
    }
    constraints = {"quality_required_fields": ["summary"]} if abstain else {}

    return TaskContract(
        task_id="int-1",
        task_type="generation",
        input_payload={"prompt": "hello"},
        output_schema=output_schema,
        constraints=constraints,
        execution_policy=policy or ExecutionPolicy(),
    )


def test_retry_then_success():
    provider = FlakyProvider(fail_times=1)
    policy = ExecutionPolicy(
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0, exponential_backoff=False),
        timeouts=TimeoutPolicy(execution_timeout_seconds=1, queue_timeout_seconds=1, total_timeout_seconds=2),
    )
    result = asyncio.run(TaskOrchestrator(provider=provider).execute(_contract(policy=policy)))

    assert provider.calls == 2
    assert result.status.value == "succeeded"


def test_timeout_results_in_failure():
    provider = SlowProvider()
    policy = ExecutionPolicy(
        retry_policy=RetryPolicy(max_attempts=1, backoff_seconds=0, exponential_backoff=False),
        timeouts=TimeoutPolicy(execution_timeout_seconds=0.01, queue_timeout_seconds=1, total_timeout_seconds=2),
    )
    result = asyncio.run(TaskOrchestrator(provider=provider).execute(_contract(policy=policy)))

    assert result.status.value == "failed"
    assert result.metadata["error"]["type"] in {"TimeoutError", "CancelledError"}


def test_provider_error_path_results_in_failure():
    provider = ErrorProvider()
    policy = ExecutionPolicy(retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0, exponential_backoff=False))
    result = asyncio.run(TaskOrchestrator(provider=provider).execute(_contract(policy=policy)))

    assert result.status.value == "failed"
    assert result.metadata["error"]["type"] == "RuntimeError"


def test_abstain_path():
    provider = MockProvider()
    result = asyncio.run(TaskOrchestrator(provider=provider).execute(_contract(abstain=True)))

    assert result.status.value == "abstained"
    assert result.final_outcome.value == "abstained"
