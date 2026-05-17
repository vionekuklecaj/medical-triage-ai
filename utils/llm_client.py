import os
from dotenv import load_dotenv


load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "openai")

def get_llm_response(prompt: str) -> str:
    if PROVIDER == "openai":
        return _call_openai(prompt)
    elif PROVIDER == "anthropic":
        return _call_anthropic(prompt)
    else:
        return "LLM provider not configured."

def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content



def _call_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
