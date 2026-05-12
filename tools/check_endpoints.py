# ABOUTME: Smoke test for LAN and cloud LLM endpoints used by showrunner agents.
# ABOUTME: Attempts a trivial completion against each endpoint and prints pass/fail.

import os
import sys
import litellm

litellm.suppress_debug_info = True

ENDPOINTS = [
    {
        "name": "Alien (llama.cpp)",
        "model": "openai/Llama-3.2-3B-Instruct-Q6_K.gguf",
        "api_base": "http://192.168.1.144:8080/v1",
        "api_key": "not-required",
    },
    {
        "name": "Sardinia (LM Studio)",
        "model": "openai/meta-llama-3.1-8b-instruct",
        "api_base": "http://192.168.1.45:1234/v1",
        "api_key": "not-required",
    },
    {
        "name": "Gemini",
        "model": "gemini/gemini-2.5-flash",
        "api_key": os.environ.get("GEMINI_API_KEY"),
        "thinking": {"type": "disabled"},
    },
]

PROMPT = [{"role": "user", "content": "Reply with one word: ready"}]


def check(endpoint: dict) -> bool:
    name = endpoint["name"]
    api_key = endpoint.get("api_key")

    if api_key is None:
        print(f"  SKIP  {name} — GEMINI_API_KEY not set")
        return True

    kwargs = {
        "model": endpoint["model"],
        "messages": PROMPT,
        "max_tokens": 64,
        "api_key": api_key,
    }
    if "api_base" in endpoint:
        kwargs["api_base"] = endpoint["api_base"]
    if "thinking" in endpoint:
        kwargs["thinking"] = endpoint["thinking"]

    try:
        response = litellm.completion(**kwargs)
        text = response.choices[0].message.content.strip()
        print(f"  PASS  {name} — {text!r}")
        return True
    except Exception as exc:
        print(f"  FAIL  {name} — {exc}")
        return False


if __name__ == "__main__":
    print("Checking endpoints...")
    results = [check(ep) for ep in ENDPOINTS]
    if all(results):
        print("\nAll endpoints OK.")
    else:
        print("\nOne or more endpoints failed.")
        sys.exit(1)
