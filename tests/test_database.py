from bkamalie.database.execute import insert_fines, insert_payment
import polars as pl


def test_insert_payment(db_mock, payment):
    db_con = db_mock.get_connection_url()
    db_con = db_con.replace("postgresql+psycopg2", "postgres")
    insert_payment(db_con, payment)
    df = pl.read_database_uri(query="SELECT * FROM payments", uri=db_con)
    assert len(df) == 1


def test_insert_fines(db_mock):
    db_con = db_mock.get_connection_url()
    db_con = db_con.replace("postgresql+psycopg2", "postgres")
    df_fines = pl.read_csv("tests/data/fines.csv")
    insert_fines(db_con, df_fines)
    df_fines_inserted = pl.read_database_uri(
        query="SELECT * FROM fine where name = 'Bagstiv eller tømmermænd'", uri=db_con
    )
    assert len(df_fines_inserted) == 1
