import json
from pathlib import Path

from app.models.quest import Environment, Mode, Quest, QuestRequest
from evaluation.run import (
    MODELS,
    SCENARIOS,
    evaluate_generation,
    run_evaluation,
    save_results,
    summarize_results,
)


class StubGenerator:
    def __init__(self, outcomes: list[Quest | Exception]) -> None:
        self.outcomes = iter(outcomes)
        self.requests: list[QuestRequest] = []

    def generate_quest(self, request: QuestRequest) -> Quest:
        self.requests.append(request)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def quest(duration_minutes: int) -> Quest:
    return Quest(
        title="Test Quest",
        duration_minutes=duration_minutes,
        difficulty=1,
        category="exploration",
        tasks=["Task one.", "Task two.", "Task three."],
    )


def request(duration_minutes: int = 30) -> QuestRequest:
    return QuestRequest(
        duration_minutes=duration_minutes,
        environment=Environment.CITY,
        mode=Mode.EXPLORE,
    )


def test_fixed_dataset_contains_all_required_scenarios() -> None:
    assert [(item.duration_minutes, item.environment.value, item.mode.value) for item in SCENARIOS] == [
        (15, "city", "explore"),
        (15, "park", "calm"),
        (15, "anywhere", "surprise"),
        (30, "nature", "explore"),
        (30, "city", "move"),
        (30, "park", "surprise"),
        (60, "nature", "calm"),
        (60, "city", "explore"),
        (60, "anywhere", "move"),
        (15, "nature", "move"),
        (30, "anywhere", "calm"),
        (60, "park", "surprise"),
    ]
    assert MODELS == ("gemma3:1b", "gemma3:4b")


def test_success_records_quest_duration_match_and_latency() -> None:
    result = evaluate_generation(
        "gemma3:1b",
        request(),
        StubGenerator([quest(30)]),
        clock=iter([10.0, 11.25]).__next__,
    )

    assert result["succeeded"] is True
    assert result["duration_matches"] is True
    assert result["latency_seconds"] == 1.25
    assert result["quest"] == quest(30).model_dump(mode="json")
    assert result["error_type"] is None
    assert result["error_message"] is None


def test_duration_mismatch_is_a_successful_evaluation_result() -> None:
    result = evaluate_generation(
        "gemma3:4b",
        request(15),
        StubGenerator([quest(30)]),
        clock=iter([4.0, 4.5]).__next__,
    )

    assert result["succeeded"] is True
    assert result["duration_matches"] is False
    assert result["quest"]["duration_minutes"] == 30


def test_failure_is_recorded_and_remaining_scenarios_continue() -> None:
    generator = StubGenerator([ValueError("invalid structure"), quest(60)])

    results = run_evaluation(
        models=["test-model"],
        scenarios=[request(30), request(60)],
        client_factory=lambda model: generator,
        clock=iter([1.0, 1.2, 2.0, 2.8]).__next__,
    )

    assert len(results) == 2
    assert results[0]["succeeded"] is False
    assert results[0]["error_type"] == "ValueError"
    assert results[0]["error_message"] == "invalid structure"
    assert results[0]["quest"] is None
    assert results[1]["succeeded"] is True
    assert len(generator.requests) == 2


def test_summary_uses_only_successful_generations_for_average_latency() -> None:
    generator = StubGenerator([quest(30), quest(15), RuntimeError("offline")])
    results = run_evaluation(
        models=["test-model"],
        scenarios=[request(30), request(30), request(30)],
        client_factory=lambda model: generator,
        clock=iter([0.0, 1.0, 2.0, 5.0, 6.0, 106.0]).__next__,
    )

    summary = summarize_results(results, models=["test-model"])[0]

    assert summary == {
        "model": "test-model",
        "successful_generations": 2,
        "total_generations": 3,
        "duration_matches": 1,
        "average_success_latency_seconds": 2.0,
    }


def test_save_results_writes_complete_json(tmp_path: Path) -> None:
    results = [
        evaluate_generation(
            "test-model",
            request(),
            StubGenerator([quest(30)]),
            clock=iter([3.0, 4.0]).__next__,
        )
    ]
    output_path = tmp_path / "nested" / "results.json"

    save_results(results, output_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == results
