"""LLM-as-judge scoring for qualitative evaluation of findings.

Uses an LLM to rate finding quality dimensions (e.g. clarity,
actionability, correctness) that are hard to measure automatically.
"""


class LLMJudge:
    """Uses an LLM to score qualitative aspects of a finding."""

    def judge(self, finding: dict) -> dict:
        """Score the given finding using an LLM judge."""
        pass
