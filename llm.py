import requests

r = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": "Bearer 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",
        "Content-Type": "application/json",
    },
    json={
        "model": "nvidia/nemotron-nano-12b-v2-vl:free",
        "messages": [{"role": "user", "content": "Hello world"}],
    },
)

data = r.json()

if "choices" in data:
    print(data["choices"][0]["message"]["content"])
else:
    print("ERROR:", data)
