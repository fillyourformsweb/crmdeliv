
import sqlite3

def check_branches():
    conn = sqlite3.connect('instance/tasks.db')
    cursor = conn.cursor()
    
    # Check if branch_new exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='branch_new'")
    if not cursor.fetchone():
        print("Table 'branch_new' does not exist!")
        return
        
    cursor.execute("SELECT id, code, name FROM branch_new")
    rows = cursor.fetchall()
    
    print("BranchNew Table Contents:")
    print("-" * 30)
    for row in rows:
        print(f"ID: {row[0]}, Code: {row[1]}, Name: {row[2]}")
    print("-" * 30)
    
    conn.close()

if __name__ == '__main__':
    check_branches()
