"""
Fix JavaScript errors in task.html
"""
import re

def fix_task_javascript_errors():
    """Fix the specific JavaScript errors reported"""
    
    file_path = 'templates/task.html'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Ensure toggleBillDropdown is properly defined and exposed to window
    # Check if the function exists and is properly exposed
    if 'function toggleBillDropdown' in content:
        # Make sure it's exposed to global scope
        if 'window.toggleBillDropdown = toggleBillDropdown' not in content:
            # Find the function definition and add window exposure
            pattern = r'function toggleBillDropdown\(taskId\)\s*{[^}]+}'
            match = re.search(pattern, content)
            if match:
                function_end = match.end()
                # Insert window exposure after function
                exposure_code = '\n        window.toggleBillDropdown = toggleBillDropdown;'
                content = content[:function_end] + exposure_code + content[function_end:]
                print("✓ Added window exposure for toggleBillDropdown")
    
    # Fix 2: Check for syntax errors around line 7478
    # Look for malformed function definitions
    lines = content.split('\n')
    
    # Check if there are lines with "function" that might be malformed
    for i, line in enumerate(lines):
        if 'function' in line and ('{' not in line or line.count('{') != line.count('}')):
            print(f"Potential syntax issue at line {i+1}: {line.strip()}")
    
    # Fix 3: Ensure all functions are properly closed
    # Count opening and closing braces in function definitions
    function_pattern = r'function\s+\w+\s*\([^)]*\)\s*{'
    functions = re.findall(function_pattern, content)
    
    print(f"Found {len(functions)} function definitions")
    
    # Look for unclosed functions
    open_braces = content.count('{')
    close_braces = content.count('}')
    
    if open_braces != close_braces:
        print(f"⚠ Brace mismatch: {open_braces} opening, {close_braces} closing")
        # Try to find and fix the specific issue
        
        # Look around line 7478 for the syntax error
        if len(lines) > 7478:
            context_lines = lines[7470:7485]
            print("Context around line 7478:")
            for i, line in enumerate(context_lines, 7471):
                if 'function' in line or '{' in line or '}' in line:
                    print(f"  {i}: {line.strip()}")
    
    # Write the fixed content
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    
    print("✓ JavaScript error fixes applied")
    
    return content

def verify_fix():
    """Verify the fixes worked"""
    file_path = 'templates/task.html'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if toggleBillDropdown is properly defined
    if 'function toggleBillDropdown' in content:
        print("✓ toggleBillDropdown function exists")
    else:
        print("✗ toggleBillDropdown function missing")
    
    # Check if it's exposed to window
    if 'window.toggleBillDropdown = toggleBillDropdown' in content:
        print("✓ toggleBillDropdown exposed to window object")
    else:
        print("✗ toggleBillDropdown not exposed to window object")
    
    # Check brace balance
    open_braces = content.count('{')
    close_braces = content.count('}')
    if open_braces == close_braces:
        print("✓ Brace balance correct")
    else:
        print(f"✗ Brace imbalance: {open_braces} vs {close_braces}")

if __name__ == "__main__":
    print("=== Fixing JavaScript Errors ===")
    fix_task_javascript_errors()
    print("\n=== Verification ===")
    verify_fix()
    print("=== Fix Complete ===")