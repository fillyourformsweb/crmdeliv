def check_parens(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    stack = []
    line = 1
    col = 1
    
    for i, char in enumerate(content):
        if char == '\n':
            line += 1
            col = 1
        else:
            col += 1
            
        if char == '(':
            stack.append(('(', line, col))
        elif char == ')':
            if not stack:
                print(f"Extra closing paren at line {line}, col {col}")
            else:
                stack.pop()
    
    if stack:
        for char, l, c in stack:
            print(f"Unclosed open paren at line {l}, col {c}")
    else:
        print("Parentheses are balanced")

check_parens('debug_script_0.js')
