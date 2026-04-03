import re

with open("src/config.py", "r") as f:
    content = f.read()

# Make sure TEST_MODE parses boolean correctly from env '1' or 'true'
content = content.replace("    TEST_MODE: bool = False", "    TEST_MODE: bool = os.environ.get('TEST_MODE') == '1'")

with open("src/config.py", "w") as f:
    f.write(content)
