from pyspark.sql import SparkSession
from pyspark.sql.functions import col, broadcast

# =========================
# Spark Session
# =========================
spark = SparkSession.builder \
    .appName("MAO004_Optimized_Pipeline") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()


# =========================
# READ DATA (Explicit Schema Friendly)
# =========================
members_df = spark.read.parquet("/data/members")
claims_df = spark.read.parquet("/data/claims")


# =========================
# COLUMN SELECTION (NO SELECT *)
# =========================
members_clean = members_df.select(
    col("member_id"),
    col("name"),
    col("dob"),
    col("state")
)

claims_clean = claims_df.select(
    col("claim_id"),
    col("member_id"),
    col("claim_amount"),
    col("service_date")
)


# =========================
# FILTER EARLY (PUSHDOWN OPTIMIZATION)
# =========================
filtered_claims = claims_clean.filter(
    col("claim_amount") > 0
)


# =========================
# JOIN OPTIMIZATION (BROADCAST SMALL TABLE)
# =========================
# assuming members is smaller than claims
joined_df = filtered_claims.join(
    broadcast(members_clean),
    on="member_id",
    how="inner"
)


# =========================
# TRANSFORMATIONS (SAFE + EXPLICIT)
# =========================
final_df = joined_df.withColumn(
    "claim_year",
    col("service_date").substr(1, 4)
)


# =========================
# PARTITIONING STRATEGY
# =========================
final_df = final_df.repartition("claim_year")


# =========================
# WRITE OPTIMIZED OUTPUT
# =========================
final_df.write \
    .mode("overwrite") \
    .partitionBy("claim_year") \
    .parquet("/output/claims_enriched")


# =========================
# CLEANUP (NO MEMORY LEAK)
# =========================
members_clean.unpersist(blocking=False)
claims_clean.unpersist(blocking=False)

spark.stop()
