with open("src/domain_models/config.py", "r") as f:
    content = f.read()

# Update the regex to exactly 64 hex characters
old_regex = r'r"^sk-or-v1-[a-zA-Z0-9]+$"'
new_regex = r'r"^sk-or-v1-[a-fA-F0-9]{64}$"'

content = content.replace(old_regex, new_regex)

with open("src/domain_models/config.py", "w") as f:
    f.write(content)
