"""
Chat Database Module
Handles all chat-related database operations using a separate SQLite database.
"""

import sqlite3
import json
from datetime import datetime, timezone
import os

# Database path
DB_PATH = os.path.join('instance', 'chat.db')

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the chat database and create tables"""
    # Ensure instance directory exists
    os.makedirs('instance', exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create chat_messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            sender_name TEXT NOT NULL,
            sender_role TEXT NOT NULL,
            message TEXT,
            file_path TEXT,
            file_name TEXT,
            file_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT 0,
            read_by TEXT DEFAULT '[]'
        )
    ''')
    
    # Create index for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON chat_messages(timestamp DESC)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sender 
        ON chat_messages(sender_id)
    ''')
    
    conn.commit()
    conn.close()
    print(f"Chat database initialized at {DB_PATH}")

def save_message(sender_id, sender_name, sender_role, message=None, 
                file_path=None, file_name=None, file_type=None):
    """Save a new chat message"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO chat_messages 
        (sender_id, sender_name, sender_role, message, file_path, file_name, file_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (sender_id, sender_name, sender_role, message, file_path, file_name, file_type))
    
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return message_id

def get_messages(limit=50, offset=0):
    """Get recent chat messages"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, sender_id, sender_name, sender_role, message, 
               file_path, file_name, file_type, timestamp, is_read, read_by
        FROM chat_messages
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    messages = []
    for row in rows:
        messages.append({
            'id': row['id'],
            'sender_id': row['sender_id'],
            'sender_name': row['sender_name'],
            'sender_role': row['sender_role'],
            'message': row['message'],
            'file_path': row['file_path'],
            'file_name': row['file_name'],
            'file_type': row['file_type'],
            'timestamp': row['timestamp'],
            'is_read': bool(row['is_read']),
            'read_by': json.loads(row['read_by']) if row['read_by'] else []
        })
    
    # Reverse to show oldest first
    messages.reverse()
    return messages

def mark_as_read(message_id, user_id):
    """Mark a message as read by a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current read_by list
    cursor.execute('SELECT read_by FROM chat_messages WHERE id = ?', (message_id,))
    row = cursor.fetchone()
    
    if row:
        read_by = json.loads(row['read_by']) if row['read_by'] else []
        
        # Add user_id if not already in list
        if user_id not in read_by:
            read_by.append(user_id)
            
            cursor.execute('''
                UPDATE chat_messages 
                SET read_by = ?, is_read = 1
                WHERE id = ?
            ''', (json.dumps(read_by), message_id))
            
            conn.commit()
    
    conn.close()

def get_unread_count(user_id):
    """Get count of unread messages for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM chat_messages
        WHERE sender_id != ? 
        AND (read_by IS NULL OR read_by NOT LIKE ?)
    ''', (user_id, f'%{user_id}%'))
    
    row = cursor.fetchone()
    conn.close()
    
    return row['count'] if row else 0

def delete_message(message_id):
    """Delete a message (admin only)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM chat_messages WHERE id = ?', (message_id,))
    
    conn.commit()
    conn.close()

def get_message_count():
    """Get total message count"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM chat_messages')
    row = cursor.fetchone()
    conn.close()
    
    return row['count'] if row else 0

# Initialize database on import
if not os.path.exists(DB_PATH):
    init_db()
