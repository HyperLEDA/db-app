def color(text: str, color: str) -> str:
    color_codes = {"blue": "94", "red": "31;20", "green": "32", "orange": "33"}
    color_code = color_codes.get(color, "0")
    return f"\033[{color_code}m{text}\x1b[0m"
