import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from time import perf_counter
from typing import Protocol, TypedDict

from app.ai.ollama_client import OllamaClient
from app.models.quest import Environment, Mode, Quest, QuestRequest


# MODELS = ("gemma3:1b", "gemma3:4b")
MODELS = ("gemma3:4b",)
SCENARIOS = (
    QuestRequest(duration_minutes=15, environment=Environment.CITY, mode=Mode.EXPLORE),
    QuestRequest(duration_minutes=15, environment=Environment.PARK, mode=Mode.CALM),
    QuestRequest(duration_minutes=15, environment=Environment.ANYWHERE, mode=Mode.SURPRISE),
    QuestRequest(duration_minutes=30, environment=Environment.NATURE, mode=Mode.EXPLORE),
    QuestRequest(duration_minutes=30, environment=Environment.CITY, mode=Mode.MOVE),
    QuestRequest(duration_minutes=30, environment=Environment.PARK, mode=Mode.SURPRISE),
    QuestRequest(duration_minutes=60, environment=Environment.NATURE, mode=Mode.CALM),
    QuestRequest(duration_minutes=60, environment=Environment.CITY, mode=Mode.EXPLORE),
    QuestRequest(duration_minutes=60, environment=Environment.ANYWHERE, mode=Mode.MOVE),
    QuestRequest(duration_minutes=15, environment=Environment.NATURE, mode=Mode.MOVE),
    QuestRequest(duration_minutes=30, environment=Environment.ANYWHERE, mode=Mode.CALM),
    QuestRequest(duration_minutes=60, environment=Environment.PARK, mode=Mode.SURPRISE),
)


class QuestGenerator(Protocol):
    def generate_quest(self, request: QuestRequest) -> Quest: ...


class EvaluationResult(TypedDict):
    model: str
    requested_duration_minutes: int
    environment: str
    mode: str
    latency_seconds: float
    succeeded: bool
    duration_matches: bool
    quest: dict[str, object] | None
    error_type: str | None
    error_message: str | None


class ModelSummary(TypedDict):
    model: str
    successful_generations: int
    total_generations: int
    duration_matches: int
    average_success_latency_seconds: float | None


def evaluate_generation(
    model: str,
    request: QuestRequest,
    generator: QuestGenerator,
    clock: Callable[[], float] = perf_counter,
) -> EvaluationResult:
    started_at = clock()

    try:
        quest = generator.generate_quest(request)
    except Exception as error:
        return {
            **_result_context(model, request, clock() - started_at),
            "succeeded": False,
            "duration_matches": False,
            "quest": None,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

    return {
        **_result_context(model, request, clock() - started_at),
        "succeeded": True,
        "duration_matches": quest.duration_minutes == request.duration_minutes,
        "quest": quest.model_dump(mode="json"),
        "error_type": None,
        "error_message": None,
    }


def run_evaluation(
    models: Sequence[str] = MODELS,
    scenarios: Sequence[QuestRequest] = SCENARIOS,
    client_factory: Callable[[str], QuestGenerator] | None = None,
    clock: Callable[[], float] = perf_counter,
) -> list[EvaluationResult]:
    create_client = client_factory or (lambda model: OllamaClient(model=model))
    results: list[EvaluationResult] = []

    for model in models:
        client = create_client(model)
        for scenario in scenarios:
            results.append(evaluate_generation(model, scenario, client, clock))

    return results


def summarize_results(
    results: Sequence[EvaluationResult],
    models: Sequence[str] = MODELS,
) -> list[ModelSummary]:
    summaries: list[ModelSummary] = []

    for model in models:
        model_results = [result for result in results if result["model"] == model]
        successful_results = [result for result in model_results if result["succeeded"]]
        duration_matches = sum(result["duration_matches"] for result in successful_results)
        average_latency = (
            sum(result["latency_seconds"] for result in successful_results)
            / len(successful_results)
            if successful_results
            else None
        )
        summaries.append(
            {
                "model": model,
                "successful_generations": len(successful_results),
                "total_generations": len(model_results),
                "duration_matches": duration_matches,
                "average_success_latency_seconds": average_latency,
            }
        )

    return summaries


def save_results(results: Sequence[EvaluationResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(list(results), indent=2) + "\n", encoding="utf-8")


def print_summary(summaries: Sequence[ModelSummary]) -> None:
    print("\nSIDEQUEST model evaluation summary")
    print("=" * 34)

    for summary in summaries:
        successful = summary["successful_generations"]
        average_latency = summary["average_success_latency_seconds"]
        latency_text = f"{average_latency:.3f} seconds" if average_latency is not None else "n/a"
        print(f"\n{summary['model']}")
        print(f"  Successful generations: {successful}/{summary['total_generations']}")
        print(f"  Duration matches:       {summary['duration_matches']}/{successful}")
        print(f"  Average success latency: {latency_text}")


def _result_context(
    model: str,
    request: QuestRequest,
    latency_seconds: float,
) -> dict[str, object]:
    return {
        "model": model,
        "requested_duration_minutes": request.duration_minutes,
        "environment": request.environment.value,
        "mode": request.mode.value,
        "latency_seconds": latency_seconds,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare SIDEQUEST generation models.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/results.json"),
        help="JSON output path (default: evaluation/results.json)",
    )
    arguments = parser.parse_args()

    results = run_evaluation()
    save_results(results, arguments.output)
    print_summary(summarize_results(results))
    print(f"\nComplete results saved to {arguments.output}")


if __name__ == "__main__":
    main()
