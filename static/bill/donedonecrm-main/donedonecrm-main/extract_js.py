import re

with open('templates/task.html', 'r', encoding='utf-8') as f:
    content = f.read()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)

for i, script in enumerate(scripts):
    with open(f'debug_script_{i}.js', 'w', encoding='utf-8') as f:
        f.write(script)
    print(f"Extracted script {i} to debug_script_{i}.js")
