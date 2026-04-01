import re

with open("src/config.py", "r") as f:
    content = f.read()

settings_lines = """
    TEST_MODE: bool = False
    ADMIN_PASSWORD: str = "admin"
    TOKEN_EXPIRY_SECONDS: int = 86400
    AI_AUTO_APPLY_CONFIDENCE: float = 0.95
    AI_MANUAL_REVIEW_THRESHOLD: float = 0.80
"""

content = content.replace("    ENVIRONMENT: str = \"development\"", "    ENVIRONMENT: str = \"development\"" + settings_lines)

with open("src/config.py", "w") as f:
    f.write(content)
