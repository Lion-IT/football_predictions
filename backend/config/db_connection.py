import os
import redis
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError

from dotenv import load_dotenv
from utils.progress_utils import create_progress_bar
from utils.logging_utils import setup_logger, log_error, log_info, log_warning

# Load environment variables from .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

# Global Redis connection
_redis_connection = None

# SQLAlchemy configuration
host = os.getenv("DB_HOST")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")
port = os.getenv("DB_PORT", 3306)

DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Logger initialization
logger = setup_logger("db_connections")

def get_redis_connection():
    """
    Returns a singleton Redis connection.
    """
    global _redis_connection
    if _redis_connection is None:
        _redis_connection = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            decode_responses=True
        )
    return _redis_connection

def execute_query(query, params=None, retries=3, delay=5):
    """
    Execute a SQL query using SQLAlchemy and connection pooling.
    Args:
        query (str): The SQL query to execute.
        params (dict or list): Parameters for the query.
    Returns:
        list or int: Query result for SELECT or affected row count for other queries.
    """
    for attempt in range(retries):
        session: Session = SessionLocal()
        try:
            result = session.execute(text(query), params)
            if query.strip().lower().startswith("select"):
                return result.fetchall()  # Return results for SELECT queries
            session.commit()  # Commit changes for INSERT/UPDATE/DELETE
            return result.rowcount  # Return affected rows for non-SELECT queries
        except OperationalError as e:
            session.rollback()  # Rollback transaction on error
            log_warning(logger, f"MySQL connection lost. Retrying... ({attempt+1}/{retries})")
            time.sleep(delay)  # Wait before retrying
        except Exception as e:
            session.rollback()  # Rollback transaction on error
            log_error(logger, f"Error executing query: {e}")
            raise
        finally:
            session.close()  # Release session back to the pool

    raise Exception("Database connection failed after multiple retries.")

def execute_many_queries(query, rows, retries=3, delay=5):
    """
    Executes a batch of queries with a progress bar.

    Args:
        query (str): SQL query string with placeholders.
        rows (list of dicts): List of dictionaries containing the data to insert/update.
    Returns:
        int: Number of affected rows.
    """
    affected_rows = 0
    batch_size = 100  # Define batch size for executemany

    with create_progress_bar(len(rows), desc="Inserting data into database", unit="rows") as pbar:
        for attempt in range(retries):
            session: Session = SessionLocal()
            try:
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    session.execute(text(query), batch)
                    session.commit()  # Commit changes for the batch
                    affected_rows += len(batch)
                    pbar.update(len(batch))  # Update progress bar
                return affected_rows
            except OperationalError as e:
                session.rollback()
                log_warning(logger, f"MySQL connection lost. Retrying batch... ({attempt+1}/{retries})")
                time.sleep(delay)
            except Exception as e:
                session.rollback()
                log_error(logger, f"Error executing query batch: {e}")
                raise
            finally:
                session.close()  # Release the session

    raise Exception("Database connection failed after multiple retries.")

def is_data_in_db(table_name, conditions):
    """
    Check if data exists in a specific table based on given conditions.
    Args:
        table_name (str): Name of the table to query.
        conditions (dict): Dictionary of column-value pairs for the WHERE clause.
    Returns:
        bool: True if data exists, False otherwise.
    """
    where_clause = " AND ".join(f"{col} = :{col}" for col in conditions.keys())
    query = f"SELECT COUNT(1) FROM {table_name} WHERE {where_clause}"

    session: Session = SessionLocal()
    try:
        result = session.execute(text(query), conditions).scalar()  # Use scalar for a single value
        return result > 0
    except Exception as e:
        log_error(logger, f"Error checking data existence: {e}")
        raise
    finally:
        session.close()

def close_connections():
    """
    Closes the global Redis connection.
    """
    global _redis_connection

    if _redis_connection:
        _redis_connection.close()
        _redis_connection = None
        log_info(logger, "Redis connection closed.")
