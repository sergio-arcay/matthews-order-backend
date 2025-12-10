import json
import re
from typing import Dict, Any, Union


def loads_json_safe(s: str, return_empty_on_failure: bool = True) -> Union[Dict[str, Any], None]:
    """
    Attempt to load JSON from a string with extensive error handling for LLM responses.

    Args:
        s: Input string that should contain JSON
        return_empty_on_failure: If True, returns {} on failure. If False, raises ValueError.

    Returns:
        Parsed JSON as dictionary, empty dict, or None based on configuration

    Handles:
    - Standard JSON
    - Markdown code blocks (```json, ```, etc.)
    - Common LLM formatting issues (trailing commas, single quotes, unquoted keys, etc.)
    - Extracting JSON-like content from surrounding text
    - Multiple JSON objects in a single string
    """

    if not s or not isinstance(s, str):
        return {} if return_empty_on_failure else None

    original_s = s
    s = s.strip()

    # Strategy 1: Try direct JSON parsing
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    json_patterns = [
        r'```json\s*\n?(.*?)\n?\s*```',  # ```json ... ```
        r'```\s*\n?(.*?)\n?\s*```',  # ``` ... ```
        r'`(.*?)`',  # `...` (single backticks)
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, s, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                cleaned = match.strip()
                if cleaned:
                    return json.loads(cleaned)
            except json.JSONDecodeError:
                continue

    # Strategy 3: Find JSON-like content between braces
    brace_patterns = [
        r'\{.*\}',  # Greedy match for outermost braces
        r'\[.*\]',  # Array format
    ]

    for pattern in brace_patterns:
        matches = re.findall(pattern, s, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

    # Strategy 4: Clean common LLM formatting issues
    cleaning_attempts = [
        # Remove common prefixes/suffixes
        lambda x: re.sub(r'^[^{[]*', '', x),  # Remove text before JSON
        lambda x: re.sub(r'[^}\]]*$', '', x),  # Remove text after JSON

        # Fix trailing commas
        lambda x: re.sub(r',(\s*[}\]])', r'\1', x),

        # Fix single quotes to double quotes (careful with contractions)
        lambda x: re.sub(r"(?<![a-zA-Z])'([^']*?)'(?=\s*:)", r'"\1"', x),  # Keys
        lambda x: re.sub(r":\s*'([^']*?)'", r': "\1"', x),  # Values

        # Fix unquoted keys
        lambda x: re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', x),

        # Fix boolean/null values that might be incorrectly quoted
        lambda x: re.sub(r':\s*"(true|false|null)"', r': \1', x, flags=re.IGNORECASE),

        # Remove comments (// or /* */)
        lambda x: re.sub(r'//.*?$', '', x, flags=re.MULTILINE),
        lambda x: re.sub(r'/\*.*?\*/', '', x, flags=re.DOTALL),

        # Fix escaped quotes issues
        lambda x: x.replace('\\"', '"').replace("\\'", "'"),

        # Remove extra whitespace and newlines
        lambda x: re.sub(r'\s+', ' ', x).strip(),
    ]

    current = s
    for clean_func in cleaning_attempts:
        try:
            current = clean_func(current)
            # Try to parse after each cleaning step
            if current.strip():
                return json.loads(current)
        except (json.JSONDecodeError, AttributeError):
            continue

    # Strategy 5: Extract multiple potential JSON objects and try each
    potential_jsons = []

    # Find all brace-enclosed content
    brace_depth = 0
    start_idx = -1

    for i, char in enumerate(s):
        if char == '{':
            if brace_depth == 0:
                start_idx = i
            brace_depth += 1
        elif char == '}':
            brace_depth -= 1
            if brace_depth == 0 and start_idx != -1:
                potential_jsons.append(s[start_idx:i + 1])

    # Try parsing each potential JSON
    for potential in potential_jsons:
        try:
            return json.loads(potential.strip())
        except json.JSONDecodeError:
            continue

    # Strategy 6: Try to extract key-value pairs manually (last resort)
    try:
        # Look for simple key: value patterns
        kv_pattern = r'["\']?(\w+)["\']?\s*:\s*["\']?([^,}\]]+)["\']?'
        matches = re.findall(kv_pattern, s)
        if matches:
            result = {}
            for key, value in matches:
                # Try to convert value to appropriate type
                value = value.strip().strip('"\'')
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.lower() == 'null':
                    value = None
                elif value.isdigit():
                    value = int(value)
                elif re.match(r'^\d+\.\d+$', value):
                    value = float(value)
                result[key] = value

            if result:
                return result
    except Exception:
        pass

    # If all strategies fail
    if return_empty_on_failure:
        return {}
    else:
        raise ValueError(f"Could not extract valid JSON from input: {original_s[:100]}...")


def extract_json_from_llm_response(response: str,
                                   expected_keys: list = None,
                                   default_values: dict = None) -> Dict[str, Any]:
    """
    Enhanced version that validates expected structure

    Args:
        response: LLM response string
        expected_keys: List of keys that should be present
        default_values: Default values for missing keys
    """
    result = loads_json_safe(response, return_empty_on_failure=True)

    if expected_keys:
        for key in expected_keys:
            if key not in result:
                if default_values and key in default_values:
                    result[key] = default_values[key]
                else:
                    result[key] = None

    return result


if __name__ == "__main__":

    test_cases = [
        '{"name": "test", "value": 123}',  # JSON válido
        '```json\n{"name": "test"}\n```',  # Markdown
        "Here's the JSON: {'name': 'sergio'}",  # Comillas simples
        '{"name": "test", "valid": true,}',  # Coma final
        '{name: "test", value: 123}',  # Claves sin comillas
        'Json array: [{"name": "item1"}, {"name": "item2"}]',  # Array JSON
        'The result is: {"status": "ok"} and that\'s it.',  # JSON embebido
    ]

    for i, test in enumerate(test_cases):
        try:
            result = loads_json_safe(test)
            print(f"Test {i + 1}: {result}")
        except Exception as e:
            print(f"Test {i + 1} failed: {e}")
