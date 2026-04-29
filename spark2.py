from pyspark.sql.functions import udf

def slow_func(x):
    return x * 2

# ❌ BAD: Python UDF (slow)
double_udf = udf(slow_func)

df = spark.read.parquet("/data/members")
df = df.withColumn("new_col", double_udf(df["id"]))
