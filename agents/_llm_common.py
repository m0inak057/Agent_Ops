"""Shared helper for specialist agents that call the OpenAI API directly.

Each specialist agent (security, code_quality, testing, devops) builds its
own system/user prompt and reads its own API key, but they all share the
same call-and-parse-JSON-findings logic, so it lives here to avoid
repeating it four times.
"""

import asyncio
import json
import logging
import os

from openai import AsyncOpenAI, RateLimitError

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
)

MODEL = os.environ.get("AUTOGEN_MODEL", "google/gemma-4-26b-a4b-it:free")
MAX_TOKENS = 2000


def _extract_json_array(content: str) -> list:
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
        content = content.strip()
    return json.loads(content)


async def call_llm_for_findings(
    system_prompt: str,
    user_prompt: str,
    agent_role: str,
    category: str,
) -> list[dict]:
    """Call the LLM and parse its response into a list of finding dicts.

    Never raises — returns an empty list on any failure so a single
    specialist agent can't take down the whole audit pipeline.
    """
    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.1,
            )
            content = response.choices[0].message.content
            findings = _extract_json_array(content)

            results = []
            for finding in findings:
                if not isinstance(finding, dict):
                    continue
                results.append(
                    {
                        "agent_role": agent_role,
                        "category": category,
                        "severity": finding.get("severity"),
                        "title": finding.get("title"),
                        "detail": finding.get("detail"),
                        "file_path": finding.get("file_path"),
                        "line_number": finding.get("line_number"),
                        "confidence": finding.get("confidence"),
                        "auto_fix_available": finding.get("auto_fix_available", False),
                    }
                )
            return results
        except RateLimitError:
            if attempt < 2:
                wait_time = (attempt + 1) * 15
                print(
                    f"Rate limited, waiting {wait_time}s before retry {attempt + 2}/3"
                )
                await asyncio.sleep(wait_time)
            else:
                print(
                    f"Rate limit exceeded after 3 attempts for agent_role={agent_role}"
                )
                return []
        except Exception as e:
            print(f"LLM call failed for agent_role={agent_role}: {e}")
            import traceback

            print(traceback.format_exc())
            return []

    return []  # fallback if loop completes without returning
