from bkamalie.app.utils import _suggest_fines
import polars as pl


def test_suggest_fines(db_mock, df_members, df_fines):
    db_con = db_mock.get_connection_url()
    db_con = db_con.replace("postgresql+psycopg2", "postgres")
    _suggest_fines(
        db_con=db_con,
        members=["Anders And", "Mickey Mouse"],
        selected_fine=["Late to Training"],
        df_fines=df_fines,
        count_fixed=1,
        count_variable=2,
        count_holdbox=0,
        df_members=df_members,
        suggested_by_user_id=3,
        comment="Traing week 12",
    )
    df = pl.read_database_uri(query="SELECT * FROM recorded_fines", uri=db_con)
    assert len(df) == 2
