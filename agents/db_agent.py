"""
Database Agent - Specialized Needle agent for database queries.
Provides tool-calling interface for database operations.
"""

import needle
from pydantic import BaseModel
from typing import Optional, List, Any
import sqlite3
import os


class DBQueryResult(BaseModel):
    """Structured database query result."""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int


class DBTableInfo(BaseModel):
    """Information about a database table."""
    name: str
    columns: List[dict]
    row_count: int


class DBSchema(BaseModel):
    """Database schema information."""
    tables: List[DBTableInfo]
    database_name: str


# In-memory database for demo purposes
DEMO_DB_PATH = "demo.db"


def _init_demo_db():
    """Initialize a demo SQLite database if it doesn't exist."""
    if not os.path.exists(DEMO_DB_PATH):
        conn = sqlite3.connect(DEMO_DB_PATH)
        cursor = conn.cursor()
        
        # Create sample tables
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                category TEXT,
                stock INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                total REAL,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        # Insert sample data
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", 
                      ("Alice Smith", "alice@example.com"))
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)",
                      ("Bob Johnson", "bob@example.com"))
        
        cursor.execute("INSERT INTO products (name, price, category, stock) VALUES (?, ?, ?, ?)",
                      ("Laptop", 999.99, "electronics", 50))
        cursor.execute("INSERT INTO products (name, price, category, stock) VALUES (?, ?, ?, ?)",
                      ("Mouse", 29.99, "electronics", 200))
        
        conn.commit()
        conn.close()


# Initialize demo database
_init_demo_db()


# Tool functions for database operations
@needle.tool
def query_db(sql: str) -> DBQueryResult:
    """Execute a SQL query on the database.
    
    Args:
        sql: SQL query string (SELECT only for safety)
    
    Returns:
        DBQueryResult with columns, rows, and count
    
    Note: For security, only SELECT queries are allowed in this demo.
    """
    sql_lower = sql.strip().lower()
    
    # Security: Only allow SELECT queries
    if not sql_lower.startswith("select"):
        return DBQueryResult(
            columns=[],
            rows=[],
            row_count=0
        )
    
    conn = sqlite3.connect(DEMO_DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        return DBQueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows)
        )
    except Exception as e:
        return DBQueryResult(
            columns=[],
            rows=[[str(e)]],
            row_count=0
        )
    finally:
        conn.close()


@needle.tool
def get_table_info(table_name: str) -> Optional[DBTableInfo]:
    """Get information about a specific table.
    
    Args:
        table_name: Name of the table
    
    Returns:
        DBTableInfo or None if table doesn't exist
    """
    conn = sqlite3.connect(DEMO_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        
        columns = []
        for col in columns_info:
            columns.append({
                "name": col[1],
                "type": col[2],
                "nullable": col[3] == 0,
                "default": col[4]
            })
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        return DBTableInfo(
            name=table_name,
            columns=columns,
            row_count=row_count
        )
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


@needle.tool
def get_schema() -> DBSchema:
    """Get the complete database schema.
    
    Returns:
        DBSchema with all tables and their information
    """
    conn = sqlite3.connect(DEMO_DB_PATH)
    cursor = conn.cursor()
    
    tables = []
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [row[0] for row in cursor.fetchall()]
    
    for table_name in table_names:
        table_info = get_table_info(table_name)
        if table_info:
            tables.append(table_info)
    
    conn.close()
    
    return DBSchema(
        tables=tables,
        database_name=DEMO_DB_PATH
    )


@needle.tool
def list_tables() -> List[str]:
    """List all tables in the database.
    
    Returns:
        List of table names
    """
    conn = sqlite3.connect(DEMO_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return tables


# Available tools for database agent
DB_TOOLS = [query_db, get_table_info, get_schema, list_tables]


class DBAgent:
    """Specialized database agent using Needle."""
    
    def __init__(self, weights: str = None, db_path: str = None):
        """Initialize database agent.
        
        Args:
            weights: Path to fine-tuned .cact file, or None for base model
            db_path: Path to SQLite database (defaults to demo.db)
        """
        self.db_path = db_path or DEMO_DB_PATH
        self.agent = needle.Needle(
            tools=DB_TOOLS,
            weights=weights,
            system="You are a database assistant. Help users query and explore databases. "
                   "Use SQL queries to retrieve data. Always sanitize inputs for security."
        )
    
    def run(self, query: str, max_steps: int = 8) -> dict:
        """Run the database agent on a query."""
        return self.agent.run(query, max_steps=max_steps)
    
    def get_tools_schema(self) -> list:
        """Get JSON schemas for all database tools."""
        return [needle.agent.tools.build_schema(tool) for tool in DB_TOOLS]
