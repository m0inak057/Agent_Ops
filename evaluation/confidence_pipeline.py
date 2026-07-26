"""Pipeline for computing confidence scores for agent findings.

Combines signals such as tool evidence, cross-agent agreement, and
LLM-judge scoring to produce a calibrated confidence score per
finding.
"""


class ConfidencePipeline:
    """Computes calibrated confidence scores for findings."""

    def score(self, finding: dict) -> float:
        """Compute a confidence score for the given finding."""
        pass
