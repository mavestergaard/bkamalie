from bkamalie.app.utils import get_secret
import polars as pl
from datetime import date, datetime


def get_connection(db_config: dict[str, str]) -> str:
    con_str = f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['db_name']}"
    return con_str


def get_db_config_from_secrets() -> dict[str, str]:
    """Get database configuration from Streamlit secrets."""
    return {
        "username": get_secret("db_username"),
        "password": get_secret("db_password"),
        "host": get_secret("db_host"),
        "port": get_secret("db_port"),
        "db_name": get_secret("db_name"),
    }


def convert_wide_to_long(input_csv_path, fine_date: date):
    """Function used to convert old excel way of storing fines to the new way of storing fines"""
    df = pl.read_csv(input_csv_path)

    df_long = df.unpivot(
        on=[col for col in df.columns if col not in ["id", "fine"]],
        index=["id", "fine"],
    )
    df_long = df_long.filter(pl.col("value").is_not_null())
    df_long = df_long.with_columns(
        fixed_count=pl.lit(1),
        variable_count=pl.col("value")
        .str.replace_many([" + ", "X", "MIN"], "")
        .replace("", 0)
        .cast(pl.Int32),
    )

    return df_long.select(
        pl.col("id").alias("fine_id"),
        pl.col("fixed_count"),
        pl.col("variable_count"),
        pl.col("variable").alias("member_id"),
        pl.lit(fine_date).alias("fine_date"),
        pl.lit("Andreas Berg Henriksen").alias("created_by"),
        pl.lit("Accepted").alias("fine_status"),
        pl.lit(datetime.now()).alias("updated_at"),
        pl.lit("Andreas Berg Henriksen").alias("updated_by"),
    )
