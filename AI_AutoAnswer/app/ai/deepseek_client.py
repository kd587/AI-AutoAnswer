import base64
import json
from dataclasses import dataclass

import cv2
from openai import OpenAI

from app.recognition.models import ObservedQuestion
from .schema import AnswerPayload, validate_answer


SYSTEM = """只回答明确允许自动化的练习选择题。仅输出 JSON 对象：
is_question(bool), question_type(single/multiple/unknown), answers(字母数组), can_answer(bool)。
不能确定时 can_answer=false 且 answers=[]。不得生成点击坐标或解析。"""


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    upper_cost_usd: float = 0.0


class AIProvider:
    def __init__(self, api_key: str, model: str = "deepseek-flash",
                 base_url: str = "https://api.deepseek.com", timeout: float = 30,
                 retries: int = 2):
        self.model = model
        self.price_per_million = {
            "deepseek-flash": (0.3, 1.2),
            "deepseek-v4-pro": (1.32, 3.96),
        }.get(model) if base_url.rstrip("/") == "https://api.deepseek.com" else None
        self.client = OpenAI(api_key=api_key, base_url=base_url,
                             timeout=timeout, max_retries=retries)
        self.usage = Usage()

    def _record(self, response) -> None:
        self.usage.calls += 1
        usage = response.usage
        if usage:
            self.usage.input_tokens += usage.prompt_tokens or 0
            self.usage.output_tokens += usage.completion_tokens or 0
            # Conservative peak, cache-miss estimate from DeepSeek pricing.
            if self.price_per_million:
                input_price, output_price = self.price_per_million
                self.usage.upper_cost_usd += ((usage.prompt_tokens or 0) * input_price
                                               + (usage.completion_tokens or 0) * output_price) / 1_000_000

    def test_connection(self) -> str:
        response = self.client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": "只回复 OK"}],
            max_tokens=32, extra_body={"thinking": {"type": "disabled"}})
        self._record(response)
        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise ValueError("API returned empty content")
        return content

    def analyze(self, observed: ObservedQuestion, image=None,
                use_vision: bool = False) -> AnswerPayload:
        user_text = json.dumps({"question_type": observed.question_type,
                                "question": observed.question,
                                "options": observed.option_text}, ensure_ascii=False)
        content = user_text
        if use_vision:
            if self.model != "deepseek-flash":
                raise ValueError("Selected model is not known to support image input")
            if image is None:
                raise ValueError("Vision requested without screenshot")
            success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not success:
                raise ValueError("Screenshot encoding failed")
            encoded = base64.b64encode(buffer.tobytes()).decode("ascii")
            content = [{"type": "text", "text": user_text},
                       {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": content}],
            response_format={"type": "json_object"}, max_tokens=150,
            extra_body={"thinking": {"type": "disabled"}})
        self._record(response)
        if response.choices[0].finish_reason == "length":
            raise ValueError("AI answer was truncated")
        payload = AnswerPayload.model_validate_json(response.choices[0].message.content or "")
        validate_answer(payload, observed.option_text)
        if observed.question_type != "unknown" and payload.question_type != observed.question_type:
            raise ValueError(f"AI 题型 {payload.question_type} 与当前控件题型 {observed.question_type} 不一致；"
                             f"识别来源 {observed.source}，请检查题目识别日志")
        return payload
