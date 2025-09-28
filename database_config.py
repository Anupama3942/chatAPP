import sqlite3
import os

def get_db_connection():
    return sqlite3.connect("cryptalk.db", check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create tables with SQLite compatible syntax
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            public_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            conv_id TEXT PRIMARY KEY,
            conv_type TEXT NOT NULL CHECK (conv_type IN ('direct', 'group')),
            members TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            msg_id TEXT PRIMARY KEY,
            conv_id TEXT,
            sender_id TEXT,
            ciphertext TEXT NOT NULL,
            iv TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conv_id) REFERENCES conversations (conv_id),
            FOREIGN KEY (sender_id) REFERENCES users (user_id)
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ SQLite Database initialized successfully!")