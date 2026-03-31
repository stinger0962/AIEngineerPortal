"""
Deployment additions to be appended to data.py.
Run: python _apply_additions.py
"""

DEPLOYMENT_EXERCISES = r'''

# ── AI Deployment & MLOps exercises ──────────────────────────────────────────
EXERCISES += [
    {
        "title": "Build a health check endpoint for an LLM service",
        "slug": "health-check-endpoint-llm-service",
        "category": "api-async",
        "difficulty": "medium",
        "prompt_md": """\
## Build a Health Check Endpoint for an LLM Service

A production LLM service needs two health endpoints with different semantics. A naive `/ping -> 200` is useless — it does not tell you whether the model is loaded, whether the provider API is reachable, or whether the service can handle a request.

### What to build

Implement a `HealthChecker` class and two endpoint functions:

1. **`HealthChecker`**:
   - `mark_fatal(reason: str)` — marks the service unrecoverable (liveness will fail)
   - `set_model_loaded(loaded: bool)`
   - `set_provider_healthy(healthy: bool)`
   - `set_cache_healthy(healthy: bool)` — non-critical

2. **`liveness_check(checker) -> tuple[dict, int]`**:
   - `({"status": "ok"}, 200)` unless fatal; `({"status": "fatal", "reason": "..."}, 503)` if fatal

3. **`readiness_check(checker) -> tuple[dict, int]`**:
   - HTTP 503 if model not loaded OR provider unhealthy
   - HTTP 200, degraded=True if only cache is unhealthy
   - HTTP 200, degraded=False if all pass

### Why this matters

In Kubernetes, liveness failure triggers a container restart; readiness failure only removes the pod from rotation. LLM services loading models at startup need generous startup probes — conflating liveness and readiness causes unnecessary restart loops.
""",
        "starter_code": """\
from dataclasses import dataclass, field


@dataclass
class HealthChecker:
    _fatal_reason: str | None = field(default=None, init=False)
    _model_loaded: bool = field(default=False, init=False)
    _provider_healthy: bool = field(default=True, init=False)
    _cache_healthy: bool = field(default=True, init=False)

    def mark_fatal(self, reason: str) -> None:
        raise NotImplementedError

    def set_model_loaded(self, loaded: bool) -> None:
        raise NotImplementedError

    def set_provider_healthy(self, healthy: bool) -> None:
        raise NotImplementedError

    def set_cache_healthy(self, healthy: bool) -> None:
        raise NotImplementedError


def liveness_check(checker: HealthChecker) -> tuple[dict, int]:
    # 200 + {"status": "ok"} unless fatal; 503 + {"status": "fatal", "reason": ...}
    raise NotImplementedError


def readiness_check(checker: HealthChecker) -> tuple[dict, int]:
    # 503 if model not loaded OR provider unhealthy
    # 200 + degraded=True if only cache unhealthy
    # 200 + degraded=False if all pass
    raise NotImplementedError
""",
        "solution_code": """\
from dataclasses import dataclass, field


@dataclass
class HealthChecker:
    _fatal_reason: str | None = field(default=None, init=False)
    _model_loaded: bool = field(default=False, init=False)
    _provider_healthy: bool = field(default=True, init=False)
    _cache_healthy: bool = field(default=True, init=False)

    def mark_fatal(self, reason: str) -> None:
        self._fatal_reason = reason

    def set_model_loaded(self, loaded: bool) -> None:
        self._model_loaded = loaded

    def set_provider_healthy(self, healthy: bool) -> None:
        self._provider_healthy = healthy

    def set_cache_healthy(self, healthy: bool) -> None:
        self._cache_healthy = healthy


def liveness_check(checker: HealthChecker) -> tuple[dict, int]:
    if checker._fatal_reason is not None:
        return {"status": "fatal", "reason": checker._fatal_reason}, 503
    return {"status": "ok"}, 200


def readiness_check(checker: HealthChecker) -> tuple[dict, int]:
    checks = {
        "model_loaded": checker._model_loaded,
        "provider_healthy": checker._provider_healthy,
        "cache_healthy": checker._cache_healthy,
    }
    if not (checks["model_loaded"] and checks["provider_healthy"]):
        return {"healthy": False, "degraded": False, "checks": checks}, 503
    degraded = not checks["cache_healthy"]
    return {"healthy": True, "degraded": degraded, "checks": checks}, 200


# Tests
c = HealthChecker()
assert liveness_check(c) == ({"status": "ok"}, 200)

c.mark_fatal("OOM")
body, status = liveness_check(c)
assert status == 503 and "OOM" in body["reason"]

c2 = HealthChecker()
assert readiness_check(c2)[1] == 503  # model not loaded

c2.set_model_loaded(True)
body, status = readiness_check(c2)
assert status == 200 and body["degraded"] is False

c2.set_cache_healthy(False)
body, status = readiness_check(c2)
assert status == 200 and body["degraded"] is True

c2.set_provider_healthy(False)
assert readiness_check(c2)[1] == 503

print("All health check tests passed.")
""",
        "explanation_md": """\
Separating critical checks (model loaded, provider reachable) from non-critical checks (cache) is the key decision. The readiness endpoint returns HTTP 200 even when cache is down — traffic flows with cache-miss overhead rather than removing a healthy pod from rotation.

`mark_fatal` handles runtime unrecoverable errors. Liveness returning 503 tells Kubernetes to restart the container — correct for OOM or config failure that cannot self-heal.

In production, wrap each dependency check in `asyncio.wait_for` with a 1-2 second timeout. A hanging provider probe must not block the health endpoint for 30 seconds during a provider outage.
""",
        "tags_json": ["deployment", "health-checks", "kubernetes", "reliability", "api-async"],
    },
    {
        "title": "Implement token-based rate limiting for an LLM API",
        "slug": "token-based-rate-limiting-llm-api",
        "category": "api-async",
        "difficulty": "medium",
        "prompt_md": """\
## Implement Token-Based Rate Limiting for an LLM API

Request-count rate limiting is insufficient for LLM services. A user sending one 100,000-token request consumes the same quota as 100 typical requests. Token-aware rate limiting is the correct model.

### What to build

`TokenRateLimiter` with a sliding window:

1. `TokenRateLimiter(max_tokens_per_minute: int, max_requests_per_minute: int)`

2. `check_and_consume(user_id: str, estimated_tokens: int) -> tuple[bool, dict]`:
   - `(True, {"allowed": True, "tokens_remaining": int, "requests_remaining": int})` if within limits
   - `(False, {"allowed": False, "reason": str, "retry_after_seconds": float})` if exceeded
   - 60-second sliding window per user

3. `get_usage(user_id: str) -> dict`

### Constraints

- Standard library only. In-memory dicts.
- Sliding window tracks actual timestamps (not fixed-minute buckets).
- Both limits enforced independently.
- Tokens consumed optimistically before the call completes.
""",
        "starter_code": """\
from __future__ import annotations
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class WindowEntry:
    timestamp: float
    tokens: int


class TokenRateLimiter:
    WINDOW_SECONDS = 60.0

    def __init__(self, max_tokens_per_minute: int, max_requests_per_minute: int):
        raise NotImplementedError

    def _evict_old_entries(self, entries: deque, now: float) -> None:
        raise NotImplementedError

    def check_and_consume(self, user_id: str, estimated_tokens: int) -> tuple[bool, dict]:
        raise NotImplementedError

    def get_usage(self, user_id: str) -> dict:
        raise NotImplementedError
""",
        "solution_code": """\
from __future__ import annotations
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class WindowEntry:
    timestamp: float
    tokens: int


class TokenRateLimiter:
    WINDOW_SECONDS = 60.0

    def __init__(self, max_tokens_per_minute: int, max_requests_per_minute: int):
        self.max_tokens = max_tokens_per_minute
        self.max_requests = max_requests_per_minute
        self._windows: dict[str, deque[WindowEntry]] = defaultdict(deque)

    def _evict_old_entries(self, entries: deque, now: float) -> None:
        cutoff = now - self.WINDOW_SECONDS
        while entries and entries[0].timestamp < cutoff:
            entries.popleft()

    def check_and_consume(self, user_id: str, estimated_tokens: int) -> tuple[bool, dict]:
        now = time.monotonic()
        entries = self._windows[user_id]
        self._evict_old_entries(entries, now)
        cur_tokens = sum(e.tokens for e in entries)
        cur_reqs = len(entries)

        if cur_tokens + estimated_tokens > self.max_tokens:
            freed = 0
            retry = self.WINDOW_SECONDS
            for entry in entries:
                freed += entry.tokens
                if freed >= (cur_tokens + estimated_tokens) - self.max_tokens:
                    retry = self.WINDOW_SECONDS - (now - entry.timestamp)
                    break
            return False, {"allowed": False, "reason": "token_limit_exceeded",
                           "retry_after_seconds": round(max(0.0, retry), 1)}

        if cur_reqs + 1 > self.max_requests:
            oldest = entries[0].timestamp if entries else now
            retry = self.WINDOW_SECONDS - (now - oldest)
            return False, {"allowed": False, "reason": "request_limit_exceeded",
                           "retry_after_seconds": round(max(0.0, retry), 1)}

        entries.append(WindowEntry(timestamp=now, tokens=estimated_tokens))
        return True, {
            "allowed": True,
            "tokens_remaining": self.max_tokens - cur_tokens - estimated_tokens,
            "requests_remaining": self.max_requests - cur_reqs - 1,
        }

    def get_usage(self, user_id: str) -> dict:
        now = time.monotonic()
        entries = self._windows[user_id]
        self._evict_old_entries(entries, now)
        return {"tokens_used": sum(e.tokens for e in entries),
                "requests_used": len(entries),
                "tokens_limit": self.max_tokens,
                "requests_limit": self.max_requests}


limiter = TokenRateLimiter(10_000, 10)
ok, info = limiter.check_and_consume("u1", 1000)
assert ok and info["tokens_remaining"] == 9000

ok, info = limiter.check_and_consume("u1", 9500)
assert not ok and info["reason"] == "token_limit_exceeded"

lim2 = TokenRateLimiter(100_000, 2)
lim2.check_and_consume("u2", 100)
lim2.check_and_consume("u2", 100)
ok, info = lim2.check_and_consume("u2", 100)
assert not ok and info["reason"] == "request_limit_exceeded"

ok, _ = limiter.check_and_consume("u3", 100)
assert ok, "Different users must be independent"
print("All rate limiter tests passed.")
""",
        "explanation_md": """\
The sliding window deque is more accurate than a fixed bucket. A fixed bucket allows two full-limit bursts within seconds of a reset boundary. The sliding window always evaluates the most recent 60-second period.

Optimistic consumption (recording the estimate before the call) is correct. Recording actual tokens after the call means the limit is not enforced until after the expensive API call has already happened.

In production, replace the in-memory dict with Redis sorted sets — `ZADD` / `ZRANGEBYSCORE` / `ZREMRANGEBYSCORE` implement a sliding window atomically across multiple service instances.
""",
        "tags_json": ["deployment", "rate-limiting", "api-async", "token-budgets", "llm-ops"],
    },
    {
        "title": "Implement A/B testing for model versions",
        "slug": "ab-testing-model-versions",
        "category": "evaluation",
        "difficulty": "medium",
        "prompt_md": """\
## Implement A/B Testing for Model Versions

Deploying a new model version without traffic splitting is risky. A/B testing routes a percentage of users to a new variant so you can measure quality before full rollout.

### What to build

`ABTestRouter(experiment_id: str, variants: list[Variant])`:

- `Variant`: `name`, `model`, `prompt_template`, `traffic_pct` (sum must be 1.0)
- `assign_variant(user_id) -> Variant` — deterministic: same user always gets same variant
- `record_outcome(user_id, variant_name, score, latency_ms)`
- `get_results() -> dict` — per-variant: `count`, `avg_score`, `avg_latency_ms`, `pass_rate` (score >= 0.7)
- `significant_winner(min_samples=30) -> str | None` — winner if leading by 0.05+ avg_score with enough samples

### Constraints

- Standard library only.
- Hash-based deterministic assignment.
- `traffic_pct` sum within 0.001 of 1.0.
""",
        "starter_code": """\
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Variant:
    name: str
    model: str
    prompt_template: str
    traffic_pct: float


class ABTestRouter:
    def __init__(self, experiment_id: str, variants: list[Variant]):
        raise NotImplementedError

    def assign_variant(self, user_id: str) -> Variant:
        raise NotImplementedError

    def record_outcome(self, user_id: str, variant_name: str, score: float, latency_ms: int) -> None:
        raise NotImplementedError

    def get_results(self) -> dict:
        raise NotImplementedError

    def significant_winner(self, min_samples: int = 30) -> str | None:
        raise NotImplementedError
""",
        "solution_code": """\
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Variant:
    name: str
    model: str
    prompt_template: str
    traffic_pct: float


@dataclass
class _Obs:
    score: float
    latency_ms: int


class ABTestRouter:
    def __init__(self, experiment_id: str, variants: list[Variant]):
        total = sum(v.traffic_pct for v in variants)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"traffic_pct must sum to 1.0, got {total:.4f}")
        self.experiment_id = experiment_id
        self.variants = variants
        self._outcomes: dict[str, list[_Obs]] = defaultdict(list)

    def assign_variant(self, user_id: str) -> Variant:
        bucket = int(hashlib.md5(f"{self.experiment_id}:{user_id}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        cumulative = 0.0
        for v in self.variants:
            cumulative += v.traffic_pct
            if bucket < cumulative:
                return v
        return self.variants[-1]

    def record_outcome(self, user_id: str, variant_name: str, score: float, latency_ms: int) -> None:
        self._outcomes[variant_name].append(_Obs(score=score, latency_ms=latency_ms))

    def get_results(self) -> dict:
        out = {}
        for v in self.variants:
            obs = self._outcomes.get(v.name, [])
            n = len(obs)
            out[v.name] = ({"count": 0, "avg_score": 0.0, "avg_latency_ms": 0.0, "pass_rate": 0.0}
                           if n == 0 else {
                               "count": n,
                               "avg_score": round(sum(o.score for o in obs) / n, 4),
                               "avg_latency_ms": round(sum(o.latency_ms for o in obs) / n, 1),
                               "pass_rate": round(sum(1 for o in obs if o.score >= 0.7) / n, 4),
                           })
        return out

    def significant_winner(self, min_samples: int = 30) -> str | None:
        results = self.get_results()
        if any(v["count"] < min_samples for v in results.values()):
            return None
        ranked = sorted(results.items(), key=lambda x: x[1]["avg_score"], reverse=True)
        if len(ranked) < 2:
            return None
        top_name, top = ranked[0]
        _, second = ranked[1]
        return top_name if top["avg_score"] - second["avg_score"] >= 0.05 else None


import random
router = ABTestRouter("exp-001", [
    Variant("control", "gpt-4o-mini", "Answer: {query}", 0.5),
    Variant("treatment", "gpt-4o", "Think: {query}", 0.5),
])
v1 = router.assign_variant("user-abc")
assert router.assign_variant("user-abc").name == v1.name, "Must be deterministic"

assignments = [router.assign_variant(f"u{i}") for i in range(1000)]
ctrl_pct = sum(1 for a in assignments if a.name == "control") / 1000
assert 0.45 <= ctrl_pct <= 0.55

random.seed(42)
for i in range(50):
    router.record_outcome(f"u{i}", "control", random.uniform(0.60, 0.75), 800)
    router.record_outcome(f"u{i}", "treatment", random.uniform(0.78, 0.95), 1200)

results = router.get_results()
assert results["control"]["count"] == 50
winner = router.significant_winner(min_samples=30)
print(f"Winner: {winner}, results: {results}")
print("All A/B test tests passed.")
""",
        "explanation_md": """\
Deterministic user assignment is what separates A/B testing from random sampling. A user seeing the treatment on Tuesday must see it on Wednesday — this is essential when measuring outcomes that occur after the initial interaction (ratings, conversions, return visits).

The 0.05 absolute difference threshold in `significant_winner` is a business heuristic, not a p-value. Production systems should use a proper statistical test (Mann-Whitney U, two-proportion z-test). Before declaring a winner, verify the actual traffic split occurred as intended and watch for novelty effects — new variants often show temporary boosts simply because they are new.
""",
        "tags_json": ["deployment", "ab-testing", "model-versioning", "evaluation", "experimentation"],
    },
    {
        "title": "Build a cost monitoring middleware",
        "slug": "cost-monitoring-middleware",
        "category": "api-async",
        "difficulty": "medium",
        "prompt_md": """\
## Build a Cost Monitoring Middleware

Without per-request cost tracking, you discover cost problems on the monthly invoice. A cost monitoring middleware intercepts every LLM call, records token usage, computes the dollar cost, and raises an alert before a budget is exceeded.

### What to build

`CostMonitor(llm_fn, budget_usd: float, model_prices: dict)`:

- `model_prices` format: `{"gpt-4o": {"input": 0.0025, "output": 0.01}}` (per 1K tokens)
- `async call(model, input_tokens, output_tokens) -> dict` — calls llm_fn, returns result with `_cost_usd`
- Raise `BudgetExceededError` BEFORE making the call if it would exceed the budget
- `get_report() -> dict` — `total_usd`, `budget_usd`, `budget_remaining_usd`, `by_model`

### Constraints

- `llm_fn` is async: `(model, input_tokens, output_tokens) -> dict`
- Standard library only
- Unknown models raise `ValueError`
""",
        "starter_code": """\
from __future__ import annotations
import asyncio
from collections import defaultdict
from dataclasses import dataclass


class BudgetExceededError(Exception):
    def __init__(self, spent_usd: float, budget_usd: float, cost_usd: float):
        self.spent_usd = spent_usd
        self.budget_usd = budget_usd
        self.cost_usd = cost_usd
        super().__init__(f"Budget exceeded: {spent_usd:.4f} + {cost_usd:.4f} > {budget_usd:.4f}")


class CostMonitor:
    def __init__(self, llm_fn, budget_usd: float, model_prices: dict[str, dict]):
        raise NotImplementedError

    def _compute_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        raise NotImplementedError

    async def call(self, model: str, input_tokens: int, output_tokens: int) -> dict:
        raise NotImplementedError

    def get_report(self) -> dict:
        raise NotImplementedError
""",
        "solution_code": """\
from __future__ import annotations
import asyncio
from collections import defaultdict
from dataclasses import dataclass


class BudgetExceededError(Exception):
    def __init__(self, spent_usd: float, budget_usd: float, cost_usd: float):
        self.spent_usd = spent_usd
        self.budget_usd = budget_usd
        self.cost_usd = cost_usd
        super().__init__(f"Budget exceeded: {spent_usd:.4f} + {cost_usd:.4f} > {budget_usd:.4f}")


@dataclass
class _Stats:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_usd: float = 0.0


class CostMonitor:
    def __init__(self, llm_fn, budget_usd: float, model_prices: dict[str, dict]):
        self._llm_fn = llm_fn
        self.budget_usd = budget_usd
        self._prices = model_prices
        self._total_usd = 0.0
        self._by_model: dict[str, _Stats] = defaultdict(_Stats)

    def _compute_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        if model not in self._prices:
            raise ValueError(f"Unknown model '{model}'")
        p = self._prices[model]
        return (input_tokens / 1000 * p["input"]) + (output_tokens / 1000 * p["output"])

    async def call(self, model: str, input_tokens: int, output_tokens: int) -> dict:
        cost = self._compute_cost(model, input_tokens, output_tokens)
        if self._total_usd + cost > self.budget_usd:
            raise BudgetExceededError(self._total_usd, self.budget_usd, cost)
        result = await self._llm_fn(model, input_tokens, output_tokens)
        self._total_usd += cost
        s = self._by_model[model]
        s.calls += 1; s.input_tokens += input_tokens
        s.output_tokens += output_tokens; s.total_usd += cost
        return {**result, "_cost_usd": cost}

    def get_report(self) -> dict:
        return {
            "total_usd": round(self._total_usd, 6),
            "budget_usd": self.budget_usd,
            "budget_remaining_usd": round(self.budget_usd - self._total_usd, 6),
            "by_model": {n: {"calls": s.calls, "input_tokens": s.input_tokens,
                             "output_tokens": s.output_tokens, "total_usd": round(s.total_usd, 6)}
                        for n, s in self._by_model.items()},
        }


import asyncio

async def mock_llm(model, input_tokens, output_tokens):
    return {"text": f"response from {model}"}

async def main():
    PRICES = {"gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
              "gpt-4o": {"input": 0.0025, "output": 0.01}}
    monitor = CostMonitor(mock_llm, budget_usd=0.01, model_prices=PRICES)

    result = await monitor.call("gpt-4o-mini", 1000, 200)
    assert "_cost_usd" in result
    expected = (1000/1000*0.00015) + (200/1000*0.0006)
    assert abs(result["_cost_usd"] - expected) < 1e-9

    try:
        await monitor.call("gpt-4o", 10000, 5000)
        assert False, "Should raise BudgetExceededError"
    except BudgetExceededError as e:
        assert e.budget_usd == 0.01
        print(f"BudgetExceededError raised: {e}")

    report = monitor.get_report()
    assert report["by_model"]["gpt-4o-mini"]["calls"] == 1
    print(f"Report: {report}")
    print("All cost monitor tests passed.")

asyncio.run(main())
""",
        "explanation_md": """\
Pre-call budget checking is correct: check before making the call, not after. The alternative means money is already spent by the time overage is detected.

The `_cost_usd` field in the return value lets downstream consumers record cost without recomputing it. Pass cost data forward through the response.

In production, budget should be per-user or per-feature, not global. A runaway loop in one feature should not block unrelated features from making calls. Alert at 80% of budget, not 100%, to provide time to investigate.
""",
        "tags_json": ["deployment", "cost-monitoring", "api-async", "llm-ops", "observability"],
    },
    {
        "title": "Implement distributed tracing spans for LLM calls",
        "slug": "distributed-tracing-spans-llm-calls",
        "category": "api-async",
        "difficulty": "medium",
        "prompt_md": """\
## Implement Distributed Tracing Spans for LLM Calls

Standard application tracing shows HTTP latency. For LLM pipelines you need per-span visibility: retrieval, prompt assembly, model call, and postprocessing — each with its own latency and metadata.

### What to build

A lightweight tracing system (no external dependencies):

1. **`Span` dataclass**: `trace_id`, `span_id`, `parent_id`, `name`, `start_time`, `end_time`, `attributes: dict`, `status` ("ok"/"error"), `error_message`. Include `duration_ms` property.

2. **`Tracer`**:
   - `start_span(name, parent=None) -> Span` — child spans inherit `parent.trace_id`
   - `finish_span(span, status="ok", error=None)`
   - `add_attribute(span, key, value)`
   - `get_trace(trace_id) -> list[Span]` — sorted by start_time
   - `export_trace(trace_id) -> list[dict]` — serializable dicts with `duration_ms`

3. **`trace_span(tracer, name, parent=None)`** context manager — starts, yields, finishes (error status on exception).

### Why it matters

Without spans, "the request took 3 seconds" tells you nothing about where time was spent. Spans reveal whether the bottleneck was retrieval, prompt assembly, or the model call.
""",
        "starter_code": """\
from __future__ import annotations
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class Span:
    trace_id: str
    span_id: str
    name: str
    start_time: float
    parent_id: str | None = None
    end_time: float | None = None
    attributes: dict = field(default_factory=dict)
    status: str = "ok"
    error_message: str | None = None

    @property
    def duration_ms(self) -> float | None:
        if self.end_time is None:
            return None
        return round((self.end_time - self.start_time) * 1000, 2)


class Tracer:
    def __init__(self):
        raise NotImplementedError

    def start_span(self, name: str, parent: Span | None = None) -> Span:
        raise NotImplementedError

    def finish_span(self, span: Span, status: str = "ok", error: str | None = None) -> None:
        raise NotImplementedError

    def add_attribute(self, span: Span, key: str, value) -> None:
        raise NotImplementedError

    def get_trace(self, trace_id: str) -> list[Span]:
        raise NotImplementedError

    def export_trace(self, trace_id: str) -> list[dict]:
        raise NotImplementedError


@contextmanager
def trace_span(tracer: Tracer, name: str, parent: Span | None = None) -> Generator[Span, None, None]:
    raise NotImplementedError
""",
        "solution_code": """\
from __future__ import annotations
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class Span:
    trace_id: str
    span_id: str
    name: str
    start_time: float
    parent_id: str | None = None
    end_time: float | None = None
    attributes: dict = field(default_factory=dict)
    status: str = "ok"
    error_message: str | None = None

    @property
    def duration_ms(self) -> float | None:
        if self.end_time is None:
            return None
        return round((self.end_time - self.start_time) * 1000, 2)


class Tracer:
    def __init__(self):
        self._traces: dict[str, list[Span]] = defaultdict(list)

    def start_span(self, name: str, parent: Span | None = None) -> Span:
        span = Span(
            trace_id=parent.trace_id if parent else str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            name=name,
            start_time=time.monotonic(),
            parent_id=parent.span_id if parent else None,
        )
        self._traces[span.trace_id].append(span)
        return span

    def finish_span(self, span: Span, status: str = "ok", error: str | None = None) -> None:
        span.end_time = time.monotonic()
        span.status = status
        span.error_message = error

    def add_attribute(self, span: Span, key: str, value) -> None:
        span.attributes[key] = value

    def get_trace(self, trace_id: str) -> list[Span]:
        return sorted(self._traces.get(trace_id, []), key=lambda s: s.start_time)

    def export_trace(self, trace_id: str) -> list[dict]:
        return [{"trace_id": s.trace_id, "span_id": s.span_id, "parent_id": s.parent_id,
                 "name": s.name, "duration_ms": s.duration_ms, "status": s.status,
                 "error_message": s.error_message, "attributes": s.attributes}
                for s in self.get_trace(trace_id)]


@contextmanager
def trace_span(tracer: Tracer, name: str, parent: Span | None = None) -> Generator[Span, None, None]:
    span = tracer.start_span(name, parent=parent)
    try:
        yield span
    except Exception as exc:
        tracer.finish_span(span, status="error", error=str(exc))
        raise
    else:
        tracer.finish_span(span, status="ok")


import time as _t

tracer = Tracer()
with trace_span(tracer, "rag_pipeline") as root:
    tracer.add_attribute(root, "user_id", "u-123")
    _t.sleep(0.01)
    with trace_span(tracer, "retrieval", parent=root) as r:
        tracer.add_attribute(r, "chunks", 5)
        _t.sleep(0.02)
    with trace_span(tracer, "llm_call", parent=root) as c:
        tracer.add_attribute(c, "model", "gpt-4o-mini")
        _t.sleep(0.05)

spans = tracer.get_trace(root.trace_id)
assert len(spans) == 3
assert all(s.status == "ok" for s in spans)
assert all(s.duration_ms > 0 for s in spans)
assert len([s for s in spans if s.parent_id == root.span_id]) == 2

try:
    with trace_span(tracer, "fail") as err_span:
        raise RuntimeError("down")
except RuntimeError:
    pass
assert any(s.status == "error" for s in tracer.get_trace(err_span.trace_id))

exported = tracer.export_trace(root.trace_id)
for s in exported:
    print(f"  {'  ' if s['parent_id'] else ''}{s['name']}: {s['duration_ms']}ms [{s['status']}]")
print("All tracing tests passed.")
""",
        "explanation_md": """\
The context manager guarantees every span is finished even when an exception occurs. Without the try/except, a failed span would have `end_time = None` and `duration_ms = None`, silently corrupting latency data.

The parent-child relationship reconstructs the call tree. Given a slow request's trace_id, you immediately see which child span consumed the most time.

In production, replace this with OpenTelemetry. The patterns are identical: `start_span()`, attributes, parent context. OTLP exporters ship to Jaeger, Honeycomb, or Datadog without changing application code.
""",
        "tags_json": ["deployment", "observability", "tracing", "llm-ops", "api-async"],
    },
    {
        "title": "Implement graceful degradation with fallback tiers",
        "slug": "graceful-degradation-fallback-tiers",
        "category": "api-async",
        "difficulty": "hard",
        "prompt_md": """\
## Implement Graceful Degradation with Fallback Tiers

When the primary LLM provider goes down, the options are: fail hard, use cached responses, try a backup model, or return a template. A degradation chain tries each tier in sequence.

### What to build

`DegradationChain(primary_fn, fallback_fn, cache_fn, template_fn)`:

- Each fn is `async (query: str) -> str | None`. `None` signals unavailability.
- `async respond(query) -> DegradationResult` — tries tiers in order, returns first non-None result
- If all return None, use a hardcoded unavailable message

`DegradationResult`: `content`, `tier: DegradationTier`, `degraded: bool`, `tiers_attempted: int`
`DegradationTier` enum: `PRIMARY`, `FALLBACK_MODEL`, `CACHED`, `TEMPLATE`

### Constraints

- Sequential (not parallel) fallback
- Exceptions from a tier are caught and treated as unavailability
""",
        "starter_code": """\
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class DegradationTier(Enum):
    PRIMARY = "primary"
    FALLBACK_MODEL = "fallback_model"
    CACHED = "cached"
    TEMPLATE = "template"


@dataclass
class DegradationResult:
    content: str
    tier: DegradationTier
    degraded: bool
    tiers_attempted: int


class DegradationChain:
    UNAVAILABLE_MESSAGE = "Our AI assistant is temporarily unavailable. Please try again shortly."

    def __init__(self, primary_fn, fallback_fn, cache_fn, template_fn):
        raise NotImplementedError

    async def respond(self, query: str) -> DegradationResult:
        raise NotImplementedError
""",
        "solution_code": """\
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class DegradationTier(Enum):
    PRIMARY = "primary"
    FALLBACK_MODEL = "fallback_model"
    CACHED = "cached"
    TEMPLATE = "template"


@dataclass
class DegradationResult:
    content: str
    tier: DegradationTier
    degraded: bool
    tiers_attempted: int


class DegradationChain:
    UNAVAILABLE_MESSAGE = "Our AI assistant is temporarily unavailable. Please try again shortly."

    def __init__(self, primary_fn, fallback_fn, cache_fn, template_fn):
        self._tiers = [
            (DegradationTier.PRIMARY, primary_fn),
            (DegradationTier.FALLBACK_MODEL, fallback_fn),
            (DegradationTier.CACHED, cache_fn),
            (DegradationTier.TEMPLATE, template_fn),
        ]

    async def respond(self, query: str) -> DegradationResult:
        for attempt, (tier, fn) in enumerate(self._tiers, start=1):
            try:
                result = await fn(query)
                if result is not None:
                    return DegradationResult(
                        content=result, tier=tier,
                        degraded=(tier != DegradationTier.PRIMARY),
                        tiers_attempted=attempt,
                    )
            except Exception as exc:
                print(f"[degradation] {tier.value} failed: {exc}")
        return DegradationResult(
            content=self.UNAVAILABLE_MESSAGE,
            tier=DegradationTier.TEMPLATE,
            degraded=True,
            tiers_attempted=len(self._tiers),
        )


import asyncio

async def main():
    async def primary(q): return f"Primary: {q}"
    async def fail_primary(q): raise ConnectionError("down")
    async def fallback(q): return f"Fallback: {q}"
    async def none_fn(q): return None

    r = await DegradationChain(primary, fallback, none_fn, none_fn).respond("test")
    assert r.tier == DegradationTier.PRIMARY and r.degraded is False and r.tiers_attempted == 1

    r2 = await DegradationChain(fail_primary, fallback, none_fn, none_fn).respond("test")
    assert r2.tier == DegradationTier.FALLBACK_MODEL and r2.degraded is True and r2.tiers_attempted == 2

    r3 = await DegradationChain(none_fn, none_fn, none_fn, none_fn).respond("test")
    assert "unavailable" in r3.content.lower() and r3.tiers_attempted == 4

    print(f"Happy path: {r.tier.value}, degraded={r.degraded}")
    print(f"Fallback path: {r2.tier.value}, attempts={r2.tiers_attempted}")
    print("All degradation chain tests passed.")

asyncio.run(main())
""",
        "explanation_md": """\
Sequential fallback is the correct design. Firing all tiers simultaneously adds unnecessary load for requests the primary handles fine. The latency cost of sequential attempts is only incurred when the primary fails.

The `tiers_attempted` field is critical for observability. Seeing it at 2 in 5% of requests signals the primary is struggling. Seeing it spike to 3-4 means both primary and fallback are degraded — the signal that warrants immediate attention.

Pair with a circuit breaker in production: once the primary fails N consecutive times, skip its timeout latency and go directly to the fallback.
""",
        "tags_json": ["deployment", "reliability", "graceful-degradation", "api-async", "circuit-breaker"],
    },
    {
        "title": "Build an observability metrics aggregator",
        "slug": "observability-metrics-aggregator",
        "category": "evaluation",
        "difficulty": "medium",
        "prompt_md": """\
## Build an Observability Metrics Aggregator

Production LLM services emit request events. An aggregator processes them into the operational metrics that matter: latency percentiles, error rates, cost by feature, quality trend.

### What to build

`LLMObservabilityAggregator` processing `RequestEvent(timestamp, feature, model, latency_ms, input_tokens, output_tokens, success, quality_score)`:

1. `ingest(event)`
2. `latency_percentiles(feature=None) -> dict` — `{"p50", "p95", "p99"}` in ms
3. `error_rate(window_minutes=60) -> float`
4. `cost_by_feature(model_prices: dict) -> dict`
5. `quality_trend(bucket_minutes=60) -> list[dict]` — `[{"bucket_start", "avg_score", "count"}]` oldest-first, only scored events

### Constraints

- Standard library only.
- Nearest-rank percentile: `ceil(p/100 * n) - 1` index into sorted array.
""",
        "starter_code": """\
from __future__ import annotations
import math
import time
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class RequestEvent:
    timestamp: float
    feature: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    success: bool
    quality_score: float | None = None


class LLMObservabilityAggregator:
    def __init__(self):
        raise NotImplementedError

    def ingest(self, event: RequestEvent) -> None:
        raise NotImplementedError

    def latency_percentiles(self, feature: str | None = None) -> dict:
        raise NotImplementedError

    def error_rate(self, window_minutes: int = 60) -> float:
        raise NotImplementedError

    def cost_by_feature(self, model_prices: dict[str, dict]) -> dict:
        raise NotImplementedError

    def quality_trend(self, bucket_minutes: int = 60) -> list[dict]:
        raise NotImplementedError
""",
        "solution_code": """\
from __future__ import annotations
import math
import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RequestEvent:
    timestamp: float
    feature: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    success: bool
    quality_score: float | None = None


class LLMObservabilityAggregator:
    def __init__(self):
        self._events: list[RequestEvent] = []

    def ingest(self, event: RequestEvent) -> None:
        self._events.append(event)

    def _pct(self, vals: list[float], p: float) -> float:
        if not vals:
            return 0.0
        sv = sorted(vals)
        return sv[max(0, math.ceil(p / 100 * len(sv)) - 1)]

    def latency_percentiles(self, feature: str | None = None) -> dict:
        ev = self._events if feature is None else [e for e in self._events if e.feature == feature]
        lat = [float(e.latency_ms) for e in ev]
        return {"p50": self._pct(lat, 50), "p95": self._pct(lat, 95), "p99": self._pct(lat, 99)}

    def error_rate(self, window_minutes: int = 60) -> float:
        cutoff = time.time() - window_minutes * 60
        win = [e for e in self._events if e.timestamp >= cutoff]
        return 0.0 if not win else sum(1 for e in win if not e.success) / len(win)

    def cost_by_feature(self, model_prices: dict[str, dict]) -> dict:
        totals: dict[str, float] = defaultdict(float)
        for e in self._events:
            p = model_prices.get(e.model)
            if p:
                totals[e.feature] += (e.input_tokens/1000*p["input"]) + (e.output_tokens/1000*p["output"])
        return {k: round(v, 6) for k, v in totals.items()}

    def quality_trend(self, bucket_minutes: int = 60) -> list[dict]:
        scored = [e for e in self._events if e.quality_score is not None]
        if not scored:
            return []
        bs = bucket_minutes * 60
        buckets: dict[int, list[float]] = defaultdict(list)
        for e in scored:
            buckets[int(e.timestamp // bs) * bs].append(e.quality_score)
        return [{"bucket_start": k, "avg_score": round(sum(s)/len(s), 4), "count": len(s)}
                for k, s in sorted(buckets.items())]


import time as _t
agg = LLMObservabilityAggregator()
now = _t.time()
PRICES = {"gpt-4o-mini": {"input": 0.00015, "output": 0.0006}, "gpt-4o": {"input": 0.0025, "output": 0.01}}

for e in [
    RequestEvent(now-3600, "chat", "gpt-4o-mini", 500, 800, 200, True, 0.9),
    RequestEvent(now-1800, "chat", "gpt-4o-mini", 800, 1200, 300, True, 0.75),
    RequestEvent(now-600, "summarize", "gpt-4o", 2000, 4000, 800, True, 0.85),
    RequestEvent(now-300, "chat", "gpt-4o-mini", 1500, 900, 150, False, None),
    RequestEvent(now-100, "chat", "gpt-4o-mini", 600, 700, 180, True, 0.6),
]:
    agg.ingest(e)

p = agg.latency_percentiles()
assert p["p50"] <= p["p95"] <= p["p99"]
assert 0 < agg.error_rate() < 1
costs = agg.cost_by_feature(PRICES)
assert "chat" in costs and "summarize" in costs
trend = agg.quality_trend(bucket_minutes=120)
assert len(trend) > 0
print(f"Percentiles: {p}, Error: {agg.error_rate():.2%}")
print(f"Costs: {costs}, Trend buckets: {len(trend)}")
print("All aggregator tests passed.")
""",
        "explanation_md": """\
The nearest-rank percentile needs no external libraries and is accurate for the sample sizes typical of LLM monitoring. For very large datasets, consider T-Digest for streaming percentile approximation.

Time-bucketed quality trend is more informative than a single rolling average. A degradation that started two hours ago would be hidden in a rolling average but is clearly visible as a bucket-to-bucket change.

In production, back this aggregator with Prometheus, InfluxDB, or TimescaleDB. The Python implementation is the right stand-in for unit-testing dashboard logic before connecting to the real backend.
""",
        "tags_json": ["deployment", "observability", "evaluation", "metrics", "llm-ops"],
    },
    {
        "title": "Build a persistent semantic cache",
        "slug": "persistent-semantic-cache",
        "category": "api-async",
        "difficulty": "hard",
        "prompt_md": """\
## Build a Persistent Semantic Cache

An in-memory semantic cache loses all entries on restart. A production semantic cache needs persistence through a key-value store, TTL-based expiration, and similarity-based lookups.

### What to build

`PersistentSemanticCache(store: dict, embedding_fn, similarity_threshold=0.92, default_ttl=3600)`:

- `CacheEntry`: `query`, `response`, `embedding`, `model`, `created_at`, `ttl_seconds`, `hit_count`. Add `is_expired` property.
- `async get(query) -> CacheEntry | None` — embed query, find best non-expired match above threshold, increment `hit_count`
- `async set(query, response, model, ttl=None) -> str` — returns cache key
- `evict_expired() -> int`
- `stats() -> dict` — `total_entries`, `expired_entries`, `total_hits`, `hit_rate`

Cache key: first 16 hex chars of `sha256(json(embedding))`.

### Constraints

- `embedding_fn` is sync: `(text) -> list[float]`
- Implement cosine similarity (no numpy)
- `store` dict simulates Redis (serialize entries as JSON strings)
""",
        "starter_code": """\
from __future__ import annotations
import hashlib, json, math, time
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    query: str
    response: str
    embedding: list[float]
    model: str
    created_at: float
    ttl_seconds: int
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        raise NotImplementedError


class PersistentSemanticCache:
    def __init__(self, store: dict, embedding_fn, similarity_threshold: float = 0.92, default_ttl: int = 3600):
        raise NotImplementedError

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        raise NotImplementedError

    def _cache_key(self, embedding: list[float]) -> str:
        raise NotImplementedError

    async def get(self, query: str) -> CacheEntry | None:
        raise NotImplementedError

    async def set(self, query: str, response: str, model: str, ttl: int | None = None) -> str:
        raise NotImplementedError

    def evict_expired(self) -> int:
        raise NotImplementedError

    def stats(self) -> dict:
        raise NotImplementedError
""",
        "solution_code": """\
from __future__ import annotations
import hashlib, json, math, time
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    query: str
    response: str
    embedding: list[float]
    model: str
    created_at: float
    ttl_seconds: int
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() > self.created_at + self.ttl_seconds


class PersistentSemanticCache:
    def __init__(self, store: dict, embedding_fn, similarity_threshold: float = 0.92, default_ttl: int = 3600):
        self._store = store
        self._embed = embedding_fn
        self._threshold = similarity_threshold
        self._default_ttl = default_ttl
        self._gets = 0
        self._hits = 0

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb) if na and nb else 0.0

    def _cache_key(self, embedding: list[float]) -> str:
        return hashlib.sha256(json.dumps(embedding, separators=(",", ":")).encode()).hexdigest()[:16]

    async def get(self, query: str) -> CacheEntry | None:
        self._gets += 1
        qe = self._embed(query)
        best_score, best = 0.0, None
        for raw in self._store.values():
            entry = CacheEntry(**json.loads(raw))
            if entry.is_expired:
                continue
            score = self._cosine_similarity(qe, entry.embedding)
            if score > best_score:
                best_score, best = score, entry
        if best and best_score >= self._threshold:
            best.hit_count += 1
            self._store[self._cache_key(best.embedding)] = json.dumps(asdict(best))
            self._hits += 1
            return best
        return None

    async def set(self, query: str, response: str, model: str, ttl: int | None = None) -> str:
        emb = self._embed(query)
        entry = CacheEntry(query=query, response=response, embedding=emb, model=model,
                           created_at=time.time(), ttl_seconds=ttl or self._default_ttl)
        key = self._cache_key(emb)
        self._store[key] = json.dumps(asdict(entry))
        return key

    def evict_expired(self) -> int:
        expired = [k for k, v in self._store.items() if CacheEntry(**json.loads(v)).is_expired]
        for k in expired:
            del self._store[k]
        return len(expired)

    def stats(self) -> dict:
        entries = [CacheEntry(**json.loads(v)) for v in self._store.values()]
        return {"total_entries": len(entries),
                "expired_entries": sum(1 for e in entries if e.is_expired),
                "total_hits": sum(e.hit_count for e in entries),
                "hit_rate": round(self._hits / self._gets, 4) if self._gets else 0.0}


import asyncio, math

def embed(text: str) -> list[float]:
    vocab = ["what", "is", "your", "return", "policy", "how", "do", "i", "get", "a", "refund"]
    vec = [1.0 if w in text.lower().split() else 0.0 for w in vocab]
    n = math.sqrt(sum(x*x for x in vec)) or 1.0
    return [x/n for x in vec]

async def main():
    store = {}
    cache = PersistentSemanticCache(store, embed, similarity_threshold=0.85)
    await cache.set("What is your return policy?", "Return items within 30 days.", "gpt-4o-mini")
    await cache.set("How do I reset my password?", "Click forgot password.", "gpt-4o-mini")
    assert len(store) == 2

    result = await cache.get("What is the return policy?")
    assert result is not None and "30 days" in result.response
    assert result.hit_count == 1

    s = cache.stats()
    assert s["total_entries"] == 2 and s["hit_rate"] > 0
    print(f"Stats: {s}, Hit: {result.response}")
    print("All semantic cache tests passed.")

asyncio.run(main())
""",
        "explanation_md": """\
Serializing entries as JSON strings mirrors how Redis stores data. `asdict()` converts the dataclass to a plain dict that `json.dumps` can serialize.

The cache key derived from the embedding is deterministic — the same query always maps to the same key. This enables O(1) exact-match lookup for identical queries. The O(n) similarity scan is only needed for near-miss detection.

Calibrate the similarity threshold using real queries. Plot the distribution of pairwise similarities — the natural gap between "same intent" and "different question" tells you where to set the threshold. Too low causes wrong-answer hits; too high misses obvious matches.
""",
        "tags_json": ["deployment", "caching", "semantic-search", "api-async", "cost-management"],
    },
]

# ── AI Deployment knowledge articles ─────────────────────────────────────────
KNOWLEDGE_ARTICLES += [
    {
        "title": "Rate limiting strategies for multi-tenant LLM services",
        "slug": "rate-limiting-strategies-multi-tenant-llm",
        "category": "deployment",
        "summary": "How to implement token-aware, multi-tier rate limiting for AI APIs — and why request-count limits alone fail for LLM workloads.",
        "content_md": """\
## Why request-count limits fail for LLM services

Standard API rate limiting counts requests per minute. This model breaks immediately for LLM workloads because request cost variance is extreme: a single 100,000-token prompt costs as much as 100 typical requests. A user who learns they can send one massive request per minute will do exactly that.

The correct model enforces two independent limits simultaneously: requests per minute AND tokens per minute.

## The two-dimension limit model

```
User quota example:
  Free tier:    60 requests/min  AND  50,000 tokens/min
  Pro tier:    120 requests/min  AND 200,000 tokens/min
  Enterprise:  unlimited req      AND custom token budget
```

A request is rejected if either limit is exceeded. The token estimate is consumed optimistically before the call — if you wait for actual token counts after the call, the limit is not enforced until after the cost has been incurred.

## Sliding window vs fixed bucket

A fixed-bucket counter resets every 60 seconds. A user who learns the reset schedule can make two full-limit bursts within seconds of a bucket boundary. The sliding window evaluates the most recent 60-second period regardless of when the clock ticks.

For the implementation, a per-user `deque` of `(timestamp, tokens)` entries is evicted on each check. Sum the tokens in the remaining entries to determine current usage.

## Multi-tier user quotas

Rate limits should be per-user, not global. A single user hitting limits should not block other users. In a multi-tenant service, implement at three levels:

- **Per-user**: primary defense against individual abuse
- **Per-feature**: prevent one feature from consuming all capacity (useful for internal services)
- **Global**: emergency circuit breaker if total service load spikes

## Communicating limits to callers

Follow HTTP conventions:
- `429 Too Many Requests` on limit exceeded
- `X-RateLimit-Limit-Requests: 60` in every response
- `X-RateLimit-Remaining-Tokens: 47,250` in every response
- `Retry-After: 14` when rate-limited (seconds until the oldest window entry expires)

The `Retry-After` header is the most important. Without it, clients that receive a 429 either retry immediately (compounding the problem) or use an arbitrary backoff that wastes quota.

## Practical considerations

**Token estimation vs actual counts.** Optimistic estimation is necessary because you do not know actual token counts until after the call. Use an approximation (4 characters per token) for enforcement, then record actual usage post-call for reporting and billing.

**Async and multi-instance deployment.** Per-instance in-memory rate limiters allow N× the intended limit when N service instances run. Production rate limiters must use Redis to maintain shared state across instances. Redis `ZADD`/`ZRANGEBYSCORE`/`ZREMRANGEBYSCORE` operations implement a sliding window atomically.

**Burst allowance.** Strict per-minute enforcement penalizes legitimate use cases (batch jobs, automated tests). Consider a burst multiplier: allow up to 2× the per-minute limit in a 10-second window before enforcing the longer-term average.
""",
        "source_links_json": ["https://platform.openai.com/docs/guides/rate-limits", "https://redis.io/docs/data-types/sorted-sets/"],
        "tags_json": ["deployment", "rate-limiting", "llm-ops", "multi-tenant", "api-design"],
    },
    {
        "title": "A/B testing and safe rollout for model deployments",
        "slug": "ab-testing-safe-rollout-model-deployments",
        "category": "deployment",
        "summary": "How to safely deploy new model versions using traffic splitting, quality metrics, and staged rollout — without full-deployment risk.",
        "content_md": """\
## The deployment risk for AI features

Deploying a new model version, prompt, or retrieval change is fundamentally different from deploying a bug fix. Code changes are verifiable: the test suite passes or fails. AI quality changes are probabilistic: average quality might improve while a specific failure mode gets worse. A new model version that improves average quality by 3% while degrading handling of edge cases by 20% is a risky trade that full-deployment-then-measure will not catch in time.

The solution is staged rollout with quality measurement at each stage.

## Traffic splitting

Route a percentage of users to the new variant while the majority uses the current version. The split must be:

**Deterministic**: the same user must always get the same variant within an experiment. If user A sees the treatment on Monday, they must see it on Tuesday when you measure follow-up behavior. Use a hash of `(experiment_id, user_id)` modulo a bucket range.

**Sticky across sessions**: if assignment changes between the user's request and their follow-up action, your quality measurements are invalid.

**Independent across experiments**: two simultaneous experiments should not interfere. Hash separately for each experiment.

## What to measure

Define quality metrics before starting the experiment:

| Metric type | Example |
|---|---|
| Outcome | User thumbs-up/down rate |
| Proxy quality | LLM-as-judge score on sampled responses |
| System | P95 latency, error rate |
| Business | Completion rate, follow-up queries |

Do not start with "we'll know it when we see it." Define pass/fail criteria before running.

## Staged rollout stages

A typical safe rollout:

1. **Internal only (0% of users)**: deploy to your team's user accounts. Catch obvious breakage without user impact.
2. **Canary (1-5%)**: small production traffic sample. Monitor error rates and latency.
3. **Small ramp (10-20%)**: enough traffic to accumulate quality signal. Run for 24-48 hours minimum.
4. **Full rollout (100%)**: only after quality metrics confirm the variant meets or exceeds the baseline.

Each stage should have an explicit "stop condition": the criteria that will trigger an automatic rollback or pause.

## Rollback plan

Always define rollback before starting. For prompt-based changes, rollback is an environment variable change (no code deployment). For model version changes, keep the previous model endpoint active during the experiment period.

## Common mistakes

**Testing with too few samples.** LLM quality metrics are noisy. A sample of 30 responses is not enough to detect a 5% quality difference. You need at minimum 200-500 responses per variant before drawing conclusions.

**Not controlling for time-of-day effects.** If your canary runs Monday morning and your control runs Friday afternoon, you are measuring time-of-day differences, not model quality. Run both variants simultaneously.

**Declaring a winner on latency alone.** A faster model that produces worse outputs is not an improvement. Always include a quality metric alongside system metrics.

**Not monitoring novelty effects.** New features often see a temporary quality boost because users engage differently with unfamiliar UI. Monitor quality over at least one full week, not just the first day of the rollout.
""",
        "source_links_json": ["https://www.optimizely.com/optimization-glossary/ab-testing/", "https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/"],
        "tags_json": ["deployment", "ab-testing", "model-versioning", "rollout", "quality"],
    },
    {
        "title": "OpenTelemetry for LLM applications: what to trace and why",
        "slug": "opentelemetry-llm-applications-tracing",
        "category": "deployment",
        "summary": "How to add span-level tracing to LLM pipelines using OpenTelemetry, and which attributes make traces actionable for debugging slow or low-quality responses.",
        "content_md": """\
## Why standard tracing falls short for LLM applications

Standard application tracing records HTTP request/response cycles. An LLM application that takes 3 seconds to respond cannot be debugged from HTTP-level traces alone — you cannot tell whether the time was spent on retrieval, embedding lookup, prompt assembly, the model call, or response parsing.

Span-level tracing breaks the pipeline into individual operations with their own latency, status, and metadata. This converts "something was slow" into "the model call was 2.8 seconds; retrieval was 80ms."

## What to instrument

### The pipeline root span

Every user-facing request should have a root span that covers the entire operation:

```python
with tracer.start_as_current_span("rag_request") as span:
    span.set_attribute("user_id", user_id)
    span.set_attribute("feature", "chat")
    span.set_attribute("session_id", session_id)
```

### Retrieval span

```python
with tracer.start_as_current_span("retrieval") as span:
    span.set_attribute("query_length_chars", len(query))
    span.set_attribute("top_k", top_k)
    results = vector_store.search(query_embedding, top_k=top_k)
    span.set_attribute("results_returned", len(results))
    span.set_attribute("top_score", results[0].score if results else 0.0)
```

The `top_score` attribute is especially useful: a score below 0.5 on the top result often indicates retrieval failure even when the number of results looks correct.

### LLM call span

```python
with tracer.start_as_current_span("llm_call") as span:
    span.set_attribute("model", model)
    span.set_attribute("input_tokens", input_tokens)
    response = client.chat(messages)
    span.set_attribute("output_tokens", response.usage.completion_tokens)
    span.set_attribute("finish_reason", response.choices[0].finish_reason)
    span.set_attribute("cost_usd", compute_cost(model, input_tokens, output_tokens))
```

The `finish_reason` attribute catches truncated responses (`length`) and content filter triggers (`content_filter`) — both are silent failures that look like normal responses in HTTP-level monitoring.

## Attributes that make traces actionable

| Attribute | Why it matters |
|---|---|
| `model` | Compare latency and quality across model versions |
| `input_tokens` | Correlate with latency and cost |
| `output_tokens` | Detect truncation |
| `finish_reason` | Catch silent failures |
| `retrieval.top_score` | Detect retrieval failure |
| `cache_hit` | Measure cache effectiveness |
| `provider_name` | Track multi-provider routing |
| `cost_usd` | Per-request cost tracking |

## Connecting traces to quality

Standard observability traces give you latency and errors. For LLM applications, add quality signals as span attributes:

```python
span.set_attribute("quality_score", judge_result.score)
span.set_attribute("quality_passed", judge_result.score >= 0.7)
span.set_attribute("faithfulness", faithfulness_score)
```

This lets you filter traces by quality: "show me all traces where `quality_passed=False` in the last hour." Without quality in traces, you debug slow requests but not poor-quality requests.

## Export targets

OpenTelemetry supports multiple backends without changing application code:

- **Jaeger** (open source): good for local development and self-hosted deployments
- **Honeycomb**: excellent for column-store querying of trace attributes
- **Datadog APM**: good if already using Datadog for infrastructure monitoring
- **LangSmith / Langfuse**: LLM-specific tracing with built-in quality tracking

The OTLP exporter is the standard: configure the endpoint and all OTLP-compatible backends accept the same traces.

## Practical setup

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://collector:4317")))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("my-llm-app")
```

The `BatchSpanProcessor` buffers spans and exports them asynchronously. The synchronous `SimpleSpanProcessor` is only appropriate for development and testing.
""",
        "source_links_json": ["https://opentelemetry.io/docs/languages/python/", "https://docs.honeycomb.io/send-data/opentelemetry/", "https://docs.smith.langchain.com/"],
        "tags_json": ["deployment", "observability", "tracing", "opentelemetry", "llm-ops"],
    },
]

# ── AI Deployment & MLOps additional interview questions ──────────────────────
INTERVIEW_QUESTIONS += [
    {
        "category": "deployment",
        "role_type": "ai-engineer",
        "difficulty": "intermediate",
        "question_text": "How do you implement token-aware rate limiting for a multi-tenant LLM API?",
        "answer_outline_md": """\
## What this question tests

The interviewer is checking whether you understand that request-count rate limiting breaks for LLM workloads, and whether you can design a practical solution that handles both dimensions of cost.

## Why request count alone fails

LLM request cost is not uniform. A single request with a 100,000-token prompt costs as much as 100 typical requests. A user on a "60 requests/minute" limit who figures this out will send 60 massive requests per minute. You need to enforce tokens per minute independently of request count.

## The two-dimension enforcement model

Enforce both simultaneously:
- **Requests per minute**: prevents API abuse and spamming
- **Tokens per minute**: prevents cost abuse through large prompts

A request is rejected if either limit is exceeded. Both are implemented as sliding windows per user.

## The sliding window implementation

```python
@dataclass
class WindowEntry:
    timestamp: float
    tokens: int

class TokenRateLimiter:
    WINDOW_SECONDS = 60.0

    def __init__(self, max_tokens_per_minute: int, max_requests_per_minute: int):
        self.max_tokens = max_tokens_per_minute
        self.max_requests = max_requests_per_minute
        self._windows: dict[str, deque[WindowEntry]] = defaultdict(deque)

    def check_and_consume(self, user_id: str, estimated_tokens: int) -> tuple[bool, dict]:
        now = time.monotonic()
        entries = self._windows[user_id]
        # Evict entries older than window
        while entries and entries[0].timestamp < now - self.WINDOW_SECONDS:
            entries.popleft()
        current_tokens = sum(e.tokens for e in entries)
        if current_tokens + estimated_tokens > self.max_tokens:
            return False, {"reason": "token_limit_exceeded"}
        if len(entries) + 1 > self.max_requests:
            return False, {"reason": "request_limit_exceeded"}
        entries.append(WindowEntry(now, estimated_tokens))
        return True, {"tokens_remaining": self.max_tokens - current_tokens - estimated_tokens}
```

## Optimistic vs pessimistic consumption

The correct approach is optimistic: consume the estimated token budget before making the call. The alternative — waiting for actual token counts from the API response — means the limit is not enforced until after the expensive call has already happened.

Use a reasonable estimate (4 characters per token) for enforcement. Record actual tokens post-call for billing and reporting.

## Multi-instance deployment

In-memory rate limiters only work for single-instance deployments. With multiple instances, each instance has its own window, allowing N× the intended limit.

Production solution: Redis sorted sets. `ZADD key score member` + `ZRANGEBYSCORE` + `ZREMRANGEBYSCORE` implement a sliding window atomically. This works correctly across all instances.

## Communicating limits to callers

Return `429 Too Many Requests` with:
- `Retry-After: <seconds>` — time until the oldest window entry expires
- `X-RateLimit-Limit-Tokens: 50000`
- `X-RateLimit-Remaining-Tokens: 0`

The `Retry-After` header prevents exponential backoff overhead on well-behaved clients.

## Interview takeaway

Two-dimension enforcement (tokens AND requests), sliding window (not fixed bucket), optimistic consumption, and Redis for multi-instance shared state. These four concepts cover the key design decisions.
""",
        "tags_json": ["deployment", "rate-limiting", "token-budgets", "api-design", "llm-ops"],
    },
    {
        "category": "deployment",
        "role_type": "ai-engineer",
        "difficulty": "advanced",
        "question_text": "Walk through how you would add distributed tracing to an LLM pipeline to diagnose latency and quality issues.",
        "answer_outline_md": """\
## What this question tests

The interviewer wants to see that you understand the difference between infrastructure observability (latency, errors) and AI-specific observability (retrieval quality, output faithfulness, cost), and that you can design a tracing implementation that surfaces both.

## The problem with HTTP-level tracing

An HTTP request that takes 3 seconds tells you nothing about where the time was spent. In an LLM pipeline, the 3 seconds might be:
- 50ms: embedding lookup
- 80ms: vector store retrieval
- 200ms: prompt assembly and token counting
- 2.5s: model API call
- 70ms: response parsing and quality scoring

Without span-level tracing, you can detect that something is slow. With spans, you know which component to optimize.

## The span model

Each pipeline stage becomes a child span of the request root:

```
trace: rag_request (3.2s)
  ├── embedding (45ms)     — input_tokens=28, model=text-embedding-3-small
  ├── retrieval (82ms)     — top_k=5, results=5, top_score=0.89
  ├── prompt_assembly (8ms) — final_tokens=1240
  ├── llm_call (2.9s)      — model=gpt-4o, input_tokens=1240, output_tokens=380, finish_reason=stop
  └── quality_check (85ms) — score=0.84, passed=True
```

## Attributes that make traces actionable

The value of a span is in its attributes. Latency alone tells you something is slow; attributes tell you why.

**LLM call span**: `model`, `input_tokens`, `output_tokens`, `finish_reason`, `cost_usd`. The `finish_reason` catches silent failures: `"length"` means the response was truncated; `"content_filter"` means the output was blocked.

**Retrieval span**: `top_k`, `results_returned`, `top_score`. A `top_score < 0.5` often indicates retrieval failure even when the correct number of chunks was returned.

**Quality span**: `quality_score`, `quality_passed`. Without quality in traces, you can find slow requests but not poor-quality requests.

## OpenTelemetry implementation

```python
from opentelemetry import trace
tracer = trace.get_tracer("rag-service")

async def handle_request(query: str, user_id: str) -> str:
    with tracer.start_as_current_span("rag_request") as root:
        root.set_attribute("user_id", user_id)
        root.set_attribute("query_length", len(query))

        with tracer.start_as_current_span("retrieval") as ret_span:
            chunks = await vector_store.search(query)
            ret_span.set_attribute("results_returned", len(chunks))
            ret_span.set_attribute("top_score", chunks[0].score if chunks else 0.0)

        with tracer.start_as_current_span("llm_call") as llm_span:
            response = await llm_client.chat(messages)
            llm_span.set_attribute("model", response.model)
            llm_span.set_attribute("input_tokens", response.usage.prompt_tokens)
            llm_span.set_attribute("output_tokens", response.usage.completion_tokens)
            llm_span.set_attribute("finish_reason", response.choices[0].finish_reason)

        return response.choices[0].message.content
```

Context propagation is automatic with OpenTelemetry — child spans inherit the trace ID from the parent without explicit plumbing.

## Connecting traces to specific failures

The power of span-based tracing emerges when you query across traces:

- "Show all traces in the last hour where `quality_score < 0.7`" — find quality failures
- "Show all traces where `finish_reason = length`" — find truncation
- "Show traces where `retrieval.top_score < 0.5`" — find retrieval failures
- "Show traces where `llm_call.duration > 5000ms`" — find tail latency

Without quality attributes in traces, the last three queries are impossible. You would have application metrics (average quality per hour) but no way to correlate poor quality with specific requests.

## Export and storage

OpenTelemetry OTLP exporter to Honeycomb, Datadog, or LangSmith. Honeycomb's column-store model is particularly good for querying trace attributes across millions of spans.

For LLM-specific tracing, LangSmith and Langfuse add pre-built views for retrieval quality, token usage, and quality scores without requiring custom attribute queries.

## Interview takeaway

The answer structure: (1) why HTTP-level traces are insufficient, (2) what spans to create and which attributes each span needs, (3) how quality signals (not just latency) get into traces, (4) how to query traces to diagnose specific failure types.
""",
        "tags_json": ["deployment", "observability", "tracing", "opentelemetry", "llm-ops"],
    },
    {
        "category": "deployment",
        "role_type": "ai-engineer",
        "difficulty": "intermediate",
        "question_text": "How do you safely roll out a new prompt version to production without risking a quality regression?",
        "answer_outline_md": """\
## What this question tests

The interviewer wants to see a concrete rollout process, not just awareness that A/B testing exists. Strong candidates describe specific stages, measurable criteria for advancing, and a clear rollback strategy.

## Why prompt deployments need special care

A prompt change that passes code review and your 50-case test suite can still cause quality regressions in production. LLM behavior is sensitive to small prompt changes in ways that are difficult to detect offline. The failure mode is not an error — it is a subtle quality shift that only shows up in long-tail cases at scale.

## The staged rollout process

### Stage 0: Offline evaluation gate

Before touching production, run the new prompt against your full evaluation suite at `temperature=0`. Use the same LLM-as-judge rubric you use in CI. The new prompt must meet or exceed the baseline on every category.

```python
# CI script
old_score = run_eval(old_prompt, cases=eval_cases)  # baseline
new_score = run_eval(new_prompt, cases=eval_cases)
assert new_score.pass_rate >= old_score.pass_rate - 0.02  # max 2% regression allowed
```

### Stage 1: Internal traffic (0% of users)

Deploy the new prompt but only route requests from internal test accounts to it. Catch obvious regressions without any user impact. Run for at least one business day.

### Stage 2: Canary (1-5%)

Route a small fraction of real users to the new prompt. Monitor:
- Error rate: any increase vs baseline?
- P95 latency: did the new prompt change response length significantly?
- User-reported thumbs-down rate (if you track it)

Run for 24 hours minimum. If any metric degrades, roll back immediately.

### Stage 3: Staged ramp (10% -> 25% -> 50%)

Each stage requires a decision: advance or roll back. The decision criteria should be defined before the rollout begins, not improvised during it.

Typical advancing criteria:
- Quality score >= baseline - 0.02 on LLM-as-judge sample
- Error rate unchanged
- P95 latency within 20% of baseline
- No spike in user-reported quality issues

### Stage 4: Full rollout (100%)

Maintain the old prompt endpoint for at least 48 hours after full rollout. If a quality issue surfaces after full rollout, rollback is a single environment variable change.

## Storing prompts for instant rollback

The rollback capability depends on how prompts are stored:

```python
# Environment variable controls which version is active
PROMPT_VERSION_SUMMARIZE = os.environ.get("PROMPT_VERSION_SUMMARIZE", "v3")
prompt = load_prompt(f"prompts/summarize_{PROMPT_VERSION_SUMMARIZE}.txt")
```

Rollback = change the environment variable. No code deployment required. This works because prompts are files under version control, not database strings.

## Sticky user assignment

During A/B stages, the same user must always see the same prompt version. If user A was in the treatment group yesterday, they must be in the treatment group today when you measure follow-up behavior.

Use a deterministic hash: `hash(experiment_id + user_id) % 100 < traffic_pct`.

## Common mistakes

**Measuring only error rate, not quality.** The new prompt might not cause errors but might produce subtly worse outputs. Always include a quality proxy metric.

**Too short a canary phase.** Quality degradation for edge cases may only show up after hundreds of requests. A 1-hour canary is not enough for most products.

**No rollback plan.** The first time you need to roll back a prompt is not when you should be designing the rollback procedure.

## Interview takeaway

The answer is a concrete sequence: offline eval gate → internal → canary → staged ramp → full rollout, with defined criteria for advancing at each stage and an instant-rollback mechanism via environment variables.
""",
        "tags_json": ["deployment", "prompt-versioning", "ab-testing", "rollout", "ci-cd"],
    },
    {
        "category": "deployment",
        "role_type": "ai-engineer",
        "difficulty": "advanced",
        "question_text": "How would you design cost monitoring and alerting for a production LLM service used by thousands of users?",
        "answer_outline_md": """\
## What this question tests

This question tests whether you have thought about AI cost as an operational concern that requires engineering controls, not just a billing metric you check monthly. Strong candidates describe granular tracking, alerting thresholds, and automatic enforcement mechanisms.

## The problem with reactive cost monitoring

Discovering a cost spike on the monthly invoice means the damage is already done. A feature with a prompt injection vulnerability or a runaway retry loop can generate tens of thousands of dollars of LLM calls before anyone notices. Reactive monitoring is not sufficient.

## What to track per request

Every LLM call should record, synchronously:

```python
@dataclass
class CostEvent:
    request_id: str
    user_id: str
    feature: str           # "chat", "summarize", "search"
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float        # computed immediately from token counts and model pricing
    timestamp: float
```

The `cost_usd` is computed at request time from a pricing table, not at billing time from the invoice. Model prices are known in advance; there is no reason to defer this computation.

## Aggregation levels

Track costs at four levels:

1. **Per request**: stored in your tracing/logging system. Enables debugging a specific expensive request.
2. **Per user, per hour**: enables detecting user-level abuse. "User X spent $12 in the last hour" is an anomaly.
3. **Per feature, per day**: enables product-level cost attribution. "The summarize feature costs $3.40/day; the chat feature costs $18.20/day."
4. **Total, per day**: the budget tracking figure. Compared against daily budget thresholds.

## Alert thresholds

Set alerts at multiple levels — do not wait for 100% budget consumption:

```
Daily budget: $100
Alert at:
  - $50 (50%): informational alert to Slack, no action required
  - $75 (75%): page on-call, investigate within 4 hours
  - $90 (90%): automatic rate limiting engaged for non-critical features
  - $100 (100%): automatic rate limiting engaged for all features except emergency path
```

The automatic enforcement at 90% is the critical mechanism. An alert without enforcement means the on-call engineer wakes up to a $200 bill.

## Per-user budget enforcement

Implement per-user daily budgets enforced at request time:

```python
async def check_user_budget(user_id: str, estimated_cost: float) -> bool:
    daily_spend = await redis.hgetfloat(f"daily_cost:{user_id}:{today()}", "total")
    if daily_spend + estimated_cost > USER_DAILY_LIMIT:
        raise UserBudgetExceededError(daily_spend, USER_DAILY_LIMIT)
    return True
```

This prevents a single user's runaway behavior from affecting the service budget.

## Model pricing table maintenance

LLM providers update pricing irregularly. A hardcoded pricing table becomes stale. Maintain it as configuration:

```python
MODEL_PRICES = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},       # per 1K tokens
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
}
```

Update this table when provider pricing changes and track it in version control. The cost of a stale pricing table is understated costs in your monitoring.

## Cost anomaly detection

Simple threshold alerts miss gradual cost increases. Implement a rolling baseline comparison:

- Compare this hour's cost to the same hour last week.
- Alert if cost is more than 3× the rolling 7-day average for that hour.
- This catches gradual increases that are individually small but cumulatively large.

## Interview takeaway

The answer covers: per-request cost recording, aggregation at multiple levels (per-user, per-feature, total), proactive alerts at multiple thresholds with automatic enforcement at the final threshold, and per-user budget limits to prevent individual abuse from affecting the service.
""",
        "tags_json": ["deployment", "cost-monitoring", "alerting", "token-budgets", "llm-ops"],
    },
    {
        "category": "deployment",
        "role_type": "ai-engineer",
        "difficulty": "advanced",
        "question_text": "Describe the observability stack you would build for a production RAG service, covering both system metrics and AI-specific signals.",
        "answer_outline_md": """\
## What this question tests

The interviewer wants to see that you understand standard observability (latency, errors, throughput) is necessary but insufficient for AI services, and that you can articulate which AI-specific signals are operationally important and how to collect them.

## Layer 1: Infrastructure metrics (necessary but insufficient)

Every production service needs these. For a RAG service, the specific values that matter:

- **P50/P95/P99 response latency**: expect high variance. P50 might be 800ms; P99 might be 12s due to long completions.
- **Error rate by error type**: distinguish provider errors (429, 500), timeout errors, validation errors, and retrieval failures. Each type has a different remediation.
- **Request throughput**: requests per minute by feature and user tier.
- **Queue depth**: if you use a request queue, queue depth predicts future latency.

## Layer 2: AI pipeline metrics

Breakdown of where latency is spent within each request:

| Metric | What it tells you |
|---|---|
| Embedding latency | Is the embedding service a bottleneck? |
| Retrieval latency | Is the vector store slow? |
| LLM call latency | Which provider is faster? |
| Prompt token count | How big are prompts? Are they growing? |
| Output token count | Are completions being truncated? |
| Cache hit rate | Is the semantic cache working? |
| Model routing distribution | How often does each model tier get used? |

These metrics are collected as span attributes in distributed traces and aggregated into time-series metrics.

## Layer 3: Quality metrics

The defining difference between AI observability and standard observability. Without quality signals, you know the service is fast and available — you do not know if it is producing good outputs.

**Quality signals at different sampling rates**:

- **Full sampling** (every request): token count, finish reason, response length. These are cheap to compute and catch truncation and formatting failures.
- **Sampled (5-10%)**: LLM-as-judge score on response quality. Too expensive to run on every request; valuable as a statistical quality indicator.
- **User-generated** (when available): thumbs up/down ratings, explicit corrections, follow-up questions that indicate confusion.

**Retrieval-specific quality**:
- Top retrieval score per request. A top score below 0.5 often indicates retrieval failure.
- Retrieval coverage: what fraction of requests retrieved any relevant chunks?
- Citation accuracy: for sampled requests, does the cited source actually support the claim?

## Layer 4: Cost observability

Cost is a first-class operational metric:
- Cost per request, segmented by model and feature
- Cost per user for multi-tenant services (to detect abuse)
- Running daily total vs daily budget with alerts at 50%, 75%, 90%

## Alerting strategy

Three levels of alerts:

**Immediate page** (P1): error rate > 5%, P99 latency > 30s, any provider completely down.

**4-hour response** (P2): quality score drops > 10% vs 24h rolling average, cache hit rate drops > 20%, cost on pace to exceed daily budget by > 50%.

**Next business day** (P3): retrieval score average declining week-over-week, specific failure categories increasing, token counts growing (prompt bloat indicator).

## Tooling recommendation

- **Traces**: OpenTelemetry with OTLP export to Honeycomb or Jaeger
- **Metrics**: Prometheus + Grafana for system metrics; InfluxDB or TimescaleDB for token/cost time series
- **Quality**: LangSmith or Langfuse for LLM-specific tracing and quality tracking
- **Alerts**: PagerDuty or OpsGenie for P1/P2; Slack for P3

## Interview takeaway

Four layers: infrastructure metrics (table stakes), pipeline breakdown (where time is spent), quality metrics (the AI-specific layer that most teams skip), and cost observability. Describe all four and explain why each layer is necessary. A monitoring system that covers only the first layer will miss the failure modes that matter most for an LLM service.
""",
        "tags_json": ["deployment", "observability", "monitoring", "rag", "llm-ops", "quality"],
    },
    {
        "category": "deployment",
        "role_type": "ai-engineer",
        "difficulty": "intermediate",
        "question_text": "How do you implement semantic caching for an LLM service, and what are the tradeoffs in choosing the similarity threshold?",
        "answer_outline_md": """\
## What this question tests

The interviewer wants to see that you understand the mechanism of semantic caching (not just that it exists), can implement it correctly, and can reason through the threshold tradeoff with concrete examples.

## What semantic caching is

An exact-match cache returns a stored response when the input is bit-for-bit identical to a previous query. Semantic caching returns a stored response when the input is semantically equivalent — similar enough in meaning that the cached answer would be appropriate.

"What is your return policy?" and "How do I return an item?" are different strings but might warrant the same cached response. Exact-match caching misses this opportunity; semantic caching catches it.

## The mechanism

1. Embed the incoming query using the same embedding model used to build the cache.
2. Compare the query embedding to stored embeddings using cosine similarity.
3. If the highest similarity score exceeds the threshold, return the cached response.
4. If not, call the LLM, store the new (query, embedding, response) entry.

```python
async def get_or_generate(query: str, generate_fn, cache: SemanticCache) -> str:
    query_embedding = embed(query)
    cached = cache.get(query_embedding)  # returns best match above threshold
    if cached:
        metrics.record("cache_hit")
        return cached.response
    response = await generate_fn(query)
    cache.set(query=query, response=response, embedding=query_embedding)
    return response
```

## The threshold tradeoff

The similarity threshold is the central parameter. It controls the tradeoff between two failure modes:

**Threshold too low (e.g., 0.75)**: cache returns responses for queries that are similar but not equivalent. "What is the return policy for electronics?" might match a cached response about apparel returns. This is a correctness failure — the user gets a wrong or irrelevant answer confidently presented.

**Threshold too high (e.g., 0.99)**: cache rarely hits because tiny phrasing variations prevent matching. "What's your return policy?" and "What is your return policy?" might not hit at a 0.99 threshold with some embedding models.

**Calibration approach**: Sample 100-200 real question pairs from your use case, manually label them as "same intent" or "different intent", and measure the cosine similarity of each pair. Find the threshold that maximizes true positives (same-intent pairs that hit) while minimizing false positives (different-intent pairs that hit). A well-calibrated threshold typically falls between 0.88 and 0.95 depending on the embedding model and domain.

## Where semantic caching is most valuable

**High value**: FAQ-style features (customer support, documentation lookup, help centers), features with repetitive question patterns, applications where user queries cluster around a small set of common intents.

**Low value**: personalized responses (the cached response for one user is wrong for another), real-time data features (responses expire quickly), highly specific technical queries (low collision rate).

**Anti-pattern**: using semantic caching for conversational chat. Each chat response depends on the conversation context; cached responses from previous conversations will be wrong.

## Implementation details

**TTL**: set expiration based on content freshness requirements. A cache entry about a return policy should expire when the policy changes — not on a fixed schedule, but on content change events. A 24-48 hour default TTL is safe for most static content.

**Cache key storage**: the cache key should be derived from the embedding (sha256 of the serialized vector), not from the raw query text. This ensures two equivalent queries with different surface forms map to nearby embeddings and both hit the cache entry for the best match.

**Redis backend**: in production, the O(n) similarity scan over in-memory entries does not scale past a few thousand entries. Use Redis Stack with the VECTOR similarity type for approximate nearest-neighbor search at scale.

## Interview takeaway

Describe the mechanism (embed, compare, serve or generate), explain the threshold tradeoff (too low: wrong answers; too high: no cache hits), give the calibration approach (label real query pairs), and identify where semantic caching adds the most value (FAQ, repetitive queries) vs where it is inappropriate (personalized, real-time, conversational).
""",
        "tags_json": ["deployment", "caching", "semantic-search", "cost-management", "embeddings"],
    },
]
'''
