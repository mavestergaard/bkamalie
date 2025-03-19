# /// script
# requires-python = ">=3.13"
# dependencies = ["schwifty"]
# ///
from schwifty import BIC
from schwifty.exceptions import InvalidLength

cb_codes = [
    "SC600516",
]


def get_bank_name(cb):
    try:
        verified_cb = BIC(cb)
        sql_join = "left join dim_bic_directory b on con.counter_bank_code = b.bic"

    except InvalidLength:
        sql_join = "left join dim_bic_directory b on regexp_replace(con.counter_bank_code, '[^0-9]', '') = b.national_id"
        return None
