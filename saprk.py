from pyspark.sql import SparkSession
from pyspark.sql.functions import udf

spark = SparkSession.builder.getOrCreate()

df = spark.read.parquet("/data/members")

df = df.select("*")

df.cache()

df = df.repartition(500)

claims = spark.read.parquet("/data/claims")

joined = df.join(claims)

result = joined.collect()

for r in result:
    print(r)
