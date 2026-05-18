import os
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "openai")


def ask_llm(system_prompt: str, user_prompt: str) -> str:
    if PROVIDER == "openai":
        return _call_openai(system_prompt, user_prompt)
    elif PROVIDER == "anthropic":
        return _call_anthropic(system_prompt, user_prompt)
    elif PROVIDER == "groq":
        return _call_groq(system_prompt, user_prompt)
    else:
        return "LLM provider not configured."


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt}, 
            {"role": "user",   "content": user_prompt}
        ]
    )
    return response.choices[0].message.content


def _call_anthropic(system_prompt: str, user_prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-6",  
        max_tokens=1024,
        system=system_prompt,       
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.content[0].text


def _call_groq(system_prompt: str, user_prompt: str) -> str:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},  # ✅ Proper system role
            {"role": "user",   "content": user_prompt}
        ]
    )
    return response.choices[0].message.content
