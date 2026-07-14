import os
import psycopg2
import pytest
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture(scope="module")
def db_connection():
    # Setup connection
    db_url = os.getenv("DATABASE_URL")
    assert db_url is not None, "DATABASE_URL environment variable is missing"
    conn = psycopg2.connect(db_url)
    yield conn
    # Teardown connection
    conn.close()

def test_db_connection_alive(db_connection):
    """Test that the Neon DB is reachable and accepts queries"""
    cur = db_connection.cursor()
    cur.execute("SELECT 1;")
    result = cur.fetchone()
    assert result[0] == 1
    cur.close()

def test_pipeline_table_exists(db_connection):
    """Test that your target pipeline table exists in Neon"""
    cur = db_connection.cursor()
    # Replace 'your_table_name' with your actual data table name
    cur.execute("""
        SELECT exists(
            SELECT * FROM information_schema.tables 
            WHERE table_name='your_table_name'
        );
    """)
    exists = cur.fetchone()[0]
    assert exists is True, "The target database table does not exist in Neon!"
    cur.close()