from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

df = spark.read.parquet("/data/members")

# ❌ BAD: pulling entire dataset to driver
data = df.collect()
df.display()

for row in data:
    print(row)
