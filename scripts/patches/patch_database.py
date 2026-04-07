import re

with open("src/database.py", "r") as f:
    content = f.read()

# Make sure we don't crash when settings.TEST_MODE doesn't exist on older object mapping if testing without proper initialization
replacement = """
import os
is_test = getattr(settings, 'TEST_MODE', False) or os.environ.get("TEST_MODE") == "1"

if is_test:
    engine = create_engine("sqlite:///:memory:")
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True
    )
"""
content = re.sub(r"import os\n# Check test mode[\s\S]*?pool_pre_ping=True\n    \)", replacement, content)

with open("src/database.py", "w") as f:
    f.write(content)
