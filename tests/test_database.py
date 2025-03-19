
from database.create_tables import insert_fines
import polars as pl

def test_insert_fines(db_mock, df_fines):
    db_con = db_mock.get_connection_url()
    db_con = db_con.replace("postgresql+psycopg2", "postgres")
    insert_fines(db_con, df_fines.drop("id"))
    df = pl.read_database_uri(query="SELECT * FROM fine", uri=db_con)
    assert len(df) == 4
