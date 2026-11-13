"""Initial PostgreSQL load. Run from a terminal for a hidden password prompt."""
from pathlib import Path
import runpy
from getpass import getpass
from sqlalchemy import create_engine, URL, text, Numeric

SCRIPT_DIR = Path(__file__).resolve().parent
data = runpy.run_path(str(SCRIPT_DIR / "01_inspect_data.py"))
tables = {
    "customers": data["customers"],
    "products": data["products_clean"],
    "orders": data["orders_clean"],
    "order_items": data["items"],
    "payments": data["payments"]
}
connection_url = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password=getpass("PostgreSQL password: "),
    host="localhost",
    port=5432,
    database="ecommerce_delivery"
)
engine = create_engine(connection_url, connect_args={"connect_timeout": 10})
money_types = {
    "order_items": {"price": Numeric(14, 2), "shipping_charges": Numeric(14, 2)},
    "payments": {"payment_value": Numeric(14, 2)}
}
try:
    with engine.begin() as connection:
        print("\nLOADING DATABASE")
        for name, df in tables.items():
            df.to_sql(
                name=name, con=connection, schema="public",
                if_exists="fail", index=False, chunksize=1000,
                method="multi", dtype=money_types.get(name)
            )
            count = connection.execute(
                text(f'SELECT COUNT(*) FROM public."{name}"')
            ).scalar_one()
            if count != len(df):
                raise ValueError(f"Row count mismatch for {name}")
            print(f"{name}: {count:,} rows verified")
    print("\nSUCCESS: All five tables saved to ecommerce_delivery.")
finally:
    engine.dispose()
