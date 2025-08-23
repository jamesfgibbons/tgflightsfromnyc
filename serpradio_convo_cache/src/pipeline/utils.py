import re, json, yaml

YAML_FENCE = re.compile(r"```(?:yaml|yml)\s*(.*?)```", re.IGNORECASE | re.DOTALL)
JSON_FENCE = re.compile(r"```json\s*(.*?)```", re.IGNORECASE | re.DOTALL)

def extract_yaml_or_json_block(text: str):
    if not text:
        return None
    # Prefer YAML block
    m = YAML_FENCE.search(text)
    if m:
        try:
            return yaml.safe_load(m.group(1))
        except Exception:
            pass
    # Fallback to JSON block
    j = JSON_FENCE.search(text)
    if j:
        try:
            return json.loads(j.group(1))
        except Exception:
            pass
    return None
