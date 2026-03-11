with open("src/infrastructure/__init__.py", "r") as f:
    content = f.read()

content = content.replace("from collections.abc import Callable\n\n", "")
with open("src/infrastructure/__init__.py", "w") as f:
    f.write(content)
