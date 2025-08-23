import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def structured_offers_from_openai(prompt: str, json_schema: dict) -> dict:
    """
    Returns dict strictly complying with json_schema using OpenAI's structured outputs.
    """
    try:
        # Use chat completions with response_format for structured outputs
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a travel pricing analyst. Return flight offers as valid JSON matching the provided schema."},
                {"role": "user", "content": prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": json_schema
            },
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    
    except Exception as e:
        print(f"⚠️ OpenAI structured call failed: {e}")
        # Return empty structure matching schema
        return {"offers": []}