"""Creates a sample dataset (with deliberate problems), baseline schema and ETL log in ./data"""
import json, pathlib
d = pathlib.Path("data"); d.mkdir(exist_ok=True)
rows = """order_id,customer_email,order_date,amount,country,discount_code
1001,a.rao@example.com,2026-11-01,250.5,IN,
1002,john@example,2026-11-01,120,US,SAVE10
1003,mei@example.com,2026-11-02,,SG,
1004,priya@example.com,11/03/2026,99.99,IN,SAVE10
1005,li@example.com,2026-11-03,310,CN,
1005,li@example.com,2026-11-03,310,CN,
1006,,2026-11-04,75,IN,
1007,sam@example.com,2026-11-04,-40,US,
1008,ana@example.com,2026-11-05,980000,BR,
1009,raj@example.com,2026-11-05,12x,IN,
1010,eva@example.com,2026-11-06,180,DE,SAVE10
1011,tom@example.com,2026-11-06,205,,
1012,zoe@example.com,2026-11-07,150,UK,
1013,kim@example.com,2026-11-07,NULL,KR,
"""
(d / "orders.csv").write_text(rows)
json.dump({"order_id": "number", "customer_email": "email", "order_date": "date",
           "amount": "number", "country": "text", "status": "text"},
          open(d / "baseline_schema.json", "w"), indent=2)
(d / "etl.log").write_text("""2026-11-17 02:00:01 INFO  Starting job load_orders
2026-11-17 02:00:09 ERROR Column 'status' not found in source extract orders_20261117.csv
2026-11-17 02:00:12 WARN  14 rows rejected: invalid date format '11/03/2026'
2026-11-17 02:00:14 ERROR Duplicate key value violates unique constraint "orders_pkey" (order_id=1005)
2026-11-17 02:00:15 ERROR NULL value in column "customer_email" violates not-null constraint
2026-11-17 02:00:22 ERROR invalid input syntax for type numeric: "12x"
2026-11-17 02:00:40 ERROR Connection timeout after 30s to warehouse-db:5432
2026-11-17 02:00:41 FATAL Job load_orders failed
""")
print("Sample data created in ./data")