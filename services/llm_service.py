"""
LLM Service for Questionnaire Summary Generation
================================================

This service provides LLM-powered summary generation for questionnaire parts.
Supports both Ollama (local) and OpenAI backends.
"""
from typing import Any, Dict, Optional
import httpx
import json

from config import settings


async def generate_summary(
    answers: Dict[str, Any],
    part_number: int,
    prompt_template: str
) -> str:
    """
    Generate AI summary for a questionnaire part.
    
    Args:
        answers: Dict of question_id -> answer_data
        part_number: Which part (1, 2, or 3)
        prompt_template: The prompt template for this part
    
    Returns:
        Generated summary text
    """
    # Format answers for the prompt
    formatted_answers = format_answers_for_prompt(answers)
    
    # Build the full prompt
    full_prompt = f"""以下是用户在法律咨询问卷第{part_number}部分中的回答：

{formatted_answers}

{prompt_template}
请提供仅对现有事实的法言法语改写
请用中文回复，保持专业但易懂的语言风格。"""

    try:
        # Try Ollama first (local)
        summary = await call_ollama(full_prompt)
        if summary:
            return summary
    except Exception as e:
        print(f"Ollama error: {e}")
    
    # Fallback: Generate simple summary without LLM
    return generate_fallback_summary(answers, part_number)


def format_answers_for_prompt(answers: Dict[str, Any]) -> str:
    """Format answers dict into a readable string for the LLM prompt."""
    lines = []
    
    for q_id, answer_data in sorted(answers.items()):
        if isinstance(answer_data, dict):
            value = answer_data.get("value", answer_data)
        else:
            value = answer_data
        
        # Format the value
        if isinstance(value, list):
            value_str = "、".join(str(v) for v in value)
        elif isinstance(value, dict):
            # Form type answer
            value_str = json.dumps(value, ensure_ascii=False)
        else:
            value_str = str(value)
        
        lines.append(f"- {q_id}: {value_str}")
    
    return "\n".join(lines)


async def call_ollama(prompt: str) -> Optional[str]:
    """
    Call Ollama API for text generation.
    
    Args:
        prompt: The prompt to send to the model
    
    Returns:
        Generated text or None if failed
    """
    ollama_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 800
        }
    }

    # For qwen3 model, disable thinking mode by adding /no_think to prompt
    # or we just use the response field which contains the actual answer
    if "qwen3" in settings.OLLAMA_MODEL.lower():
        # Add instruction to skip thinking for faster response
        payload["prompt"] = "/no_think\n" + prompt

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            print(f"Calling Ollama: {settings.OLLAMA_MODEL}")
            response = await client.post(ollama_url, json=payload)
            response.raise_for_status()

            result = response.json()
            print(f"Ollama response received, done: {result.get('done')}")

            # Get the response text (not the thinking)
            response_text = result.get("response", "").strip()

            if response_text:
                return response_text
            else:
                print("Ollama returned empty response")
                return None

        except httpx.HTTPStatusError as e:
            print(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.TimeoutException:
            print("Ollama timeout (120s)")
            return None
        except Exception as e:
            print(f"Ollama error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None


def generate_fallback_summary(answers: Dict[str, Any], part_number: int) -> str:
    """
    Generate a simple summary without LLM when service is unavailable.
    """
    answer_count = len(answers)

    part_names = {
        1: "基本信息采集",
        2: "事故过程与责任认定",
        3: "保险与赔偿信息"
    }

    part_name = part_names.get(part_number, f"第{part_number}部分")

    # Extract key information if available
    key_info = []

    if "q1" in answers and part_number == 1:
        val = answers["q1"].get("value") if isinstance(answers["q1"], dict) else answers["q1"]
        key_info.append(f"是否遭遇交通事故: {val}")

    if "q2" in answers and part_number == 1:
        val = answers["q2"].get("value") if isinstance(answers["q2"], dict) else answers["q2"]
        key_info.append(f"事故类别: {val}")

    if "q10" in answers and part_number == 2:
        val = answers["q10"].get("value") if isinstance(answers["q10"], dict) else answers["q10"]
        key_info.append(f"是否有责任认定: {val}")

    if "q13" in answers and part_number == 3:
        val = answers["q13"].get("value") if isinstance(answers["q13"], dict) else answers["q13"]
        key_info.append(f"是否有交强险: {val}")

    summary = f"【{part_name}】已完成，共回答{answer_count}个问题。"

    if key_info:
        summary += "\n\n关键信息：\n" + "\n".join(f"• {info}" for info in key_info)

    summary += "\n\n（注：LLM服务暂时不可用，此为基础摘要）"

    return summary


async def analyze_case(
    all_answers: Dict[str, Any],
    all_summaries: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform comprehensive case analysis after questionnaire completion.

    Args:
        all_answers: All answers from all parts
        all_summaries: Generated summaries for each part

    Returns:
        Analysis result with recommendations
    """
    # Build analysis prompt
    prompt = """作为法律顾问AI，请基于以下交通事故案件信息进行综合分析：

【案件摘要】
"""

    for part_key, summary_data in all_summaries.items():
        content = summary_data.get("content") if isinstance(summary_data, dict) else summary_data
        prompt += f"\n{content}\n"

    prompt += """
请提供仅对现有事实的法律解析，不做出任何对可能发生情况的分析

请用专业但易懂的中文回复。"""

    try:
        analysis = await call_ollama(prompt)
        if analysis:
            return {
                "success": True,
                "analysis": analysis,
                "generated_at": None  # Will be set by caller
            }
    except Exception as e:
        print(f"Analysis error: {e}")

    return {
        "success": False,
        "analysis": "案件分析服务暂时不可用，请联系律师进行详细分析。",
        "generated_at": None
    }