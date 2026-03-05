import os

path = 'd:/deleviry-crm420-main/deleviry-crm420-main/static/bill/donedonecrm-main/donedonecrm-main/templates/chat_widget.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the duplicate closure
content = content.replace("const currentUserId = {{ session.get('user_id', 0) }};};", "const currentUserId = {{ session.get('user_id', 0) }};")

# Also ensure indentation is consistent for the de-indented block
# From:
# 468:             const currentUserId = {{ session.get('user_id', 0) }};
# 469:     const shouldScroll = ...
# To:
# 468:             const currentUserId = {{ session.get('user_id', 0) }};
# 469:             const shouldScroll = ...

lines = content.splitlines()
new_lines = []
in_render_messages = False
for line in lines:
    if "function renderMessages(messages) {" in line:
        in_render_messages = True
        new_lines.append(line)
        continue
    
    if in_render_messages:
        if line.strip() == "}": # End of function
            in_render_messages = False
            new_lines.append(line)
            continue
        
        # If line is inside function but not indented, fix it
        if line.strip() and not line.startswith("            ") and not line.startswith("        "):
             new_lines.append("            " + line.strip())
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write("\n".join(new_lines) + "\n")

print("Fixed chat_widget.html closure and indentation")
