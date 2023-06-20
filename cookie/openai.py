import json
import time
import logging
import openai
from cachetools import LRUCache, cached

logger = logging.getLogger(__file__)


class ChatSession:
    def __init__(self, model: str = "gpt-4", max_tokens: int = 300) -> None:
        self.messages: list[dict] = []
        self.model = model
        self.max_tokens = max_tokens

    def setup(self, system_prompt: str):
        self.messages = [
            {"role": "system", "content": system_prompt},
        ]

    def respond(self, prompt: str) -> str:
        self.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        response_text = chat_completion(
            messages=self.messages, model=self.model, max_tokens=self.max_tokens
        )

        self.messages.append({"role": "assistant", "content": response_text})

        return response_text


@cached(
    LRUCache(maxsize=256),
    key=lambda messages, model, max_tokens: json.dumps(
        {"messages": messages, "model": model, "max_tokens": max_tokens}
    ),
)
def chat_completion(
    messages: list[dict], model: str = "gpt-4", max_tokens: int = 500
) -> str:
    logger.info(f"Prompting openai {model=} {max_tokens=}")
    t = time.time()
    completion = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0,
    )
    logger.info(f"Done prompting openai after {time.time() - t} seconds")

    return completion["choices"][0]["message"]["content"]
