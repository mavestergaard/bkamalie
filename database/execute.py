from database.model import Payment
import polars as pl
from psycopg2.extras import execute_values
import psycopg2
from holdsport.api import FINEBOX_ADMIN_MEMBER_ID

create_tables_sql = """
-- Enum types for FineStatus and FineCategory
DO $$ BEGIN
    CREATE TYPE fine_status AS ENUM ('Accepted', 'Declined', 'Pending');
    CREATE TYPE fine_category AS ENUM ('Training', 'Match', 'Other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Fine table
CREATE TABLE IF NOT EXISTS fine (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    fixed_amount INTEGER NOT NULL,
    variable_amount INTEGER NOT NULL,
    holdbox_amount INTEGER NOT NULL,
    description TEXT,
    category fine_category NOT NULL
);

-- Payment table
CREATE TABLE IF NOT EXISTS payment (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    payment_date TIMESTAMP NOT NULL
);

-- RecordedFines table
CREATE TABLE IF NOT EXISTS recorded_fines (
    id SERIAL PRIMARY KEY,
    fine_id INTEGER NOT NULL,
    fixed_count INTEGER NOT NULL,
    variable_count INTEGER NOT NULL,
    holdbox_count INTEGER NOT NULL,
    fined_member_id INTEGER NOT NULL,
    fine_date DATE NOT NULL,
    created_by_member_id INTEGER NOT NULL,
    fine_status fine_status NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    updated_by_member_id INTEGER NOT NULL,
    total_fine INTEGER NOT NULL,
    CONSTRAINT fk_fine FOREIGN KEY (fine_id) REFERENCES fine(id)
);
"""

def execute_query(con: str, query: str) -> bool:
    with psycopg2.connect(con) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            conn.commit()


def create_tables(con:str)-> None:
    execute_query(con, create_tables_sql)


def insert_payment(con:str, payment: Payment)-> None:
    execute_query(con, "INSERT INTO payment (member_id, amount, payment_date) VALUES (%s, %s, %s)", (payment.member_id, payment.amount, payment.payment_date))

def insert_fines(con: str, df: pl.DataFrame) -> None:
    query = f"""
        INSERT INTO fine (name, fixed_amount, variable_amount, holdbox_amount, description, category)
        VALUES %s;
    """
    with psycopg2.connect(con) as conn:
        with conn.cursor() as cursor:
            execute_values(cursor, query, df.rows())

def insert_recorded_fines(con: str, df: pl.DataFrame) -> None:
    if "id" in df.columns:
        df = df.drop("id")
    query = """
        INSERT INTO recorded_fines (fine_id, fixed_count, variable_count, holdbox_count, fined_member_id, fine_date, created_by_member_id, fine_status, updated_at, updated_by_member_id, total_fine)
        VALUES %s
    """
    with psycopg2.connect(con) as conn:
        with conn.cursor() as cursor:
            execute_values(cursor, query, df.rows())


def upsert_recorded_fines(con: str, df: pl.DataFrame) -> None:
    query = """
        INSERT INTO recorded_fines (id, fine_id, fixed_count, variable_count, holdbox_count, fined_member_id, fine_date, created_by_member_id, fine_status, updated_at, updated_by_member_id, total_fine)
        VALUES %s
        ON CONFLICT (id) DO UPDATE
            SET fine_status  = excluded.fine_status,
            updated_at = CURRENT_TIMESTAMP,
            updated_by_member_id = excluded.updated_by_member_id;
    """
    with psycopg2.connect(con) as conn:
        with conn.cursor() as cursor:
            execute_values(cursor, query, df.rows())