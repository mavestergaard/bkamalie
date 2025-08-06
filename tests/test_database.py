from bkamalie.database.execute import insert_payment
import polars as pl


def test_insert_payment(db_mock, payment):
    db_con = db_mock.get_connection_url()
    db_con = db_con.replace("postgresql+psycopg2", "postgres")
    insert_payment(db_con, payment)
    df = pl.read_database_uri(query="SELECT * FROM payments", uri=db_con)
    assert len(df) == 1
