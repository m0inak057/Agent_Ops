"""API routes for the evaluation subsystem.

Exposes endpoints to trigger evaluation runs against the benchmark
dataset and retrieve evaluation metrics/results.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/")
async def run_evaluation():
    """Trigger an evaluation run against the benchmark dataset."""
    pass


@router.get("/{evaluation_id}")
async def get_evaluation(evaluation_id: str):
    """Retrieve results for a single evaluation run."""
    pass
