from pyspark.sql.functions import col, countDistinct, count, sum as spark_sum, mean, when
from config.sparkConfig import SparkConnection, DB_URL, DB_PROPERTIES
import logging

def process_stay_locations():
    global logger
    spark = None
    try:
        # Initialize Spark
        spark = SparkConnection()
        spark.sparkContext.setLogLevel("WARN")
        logger = logging.getLogger(__name__)

        logger.info("Reading data from stay_location_data table...")
        # Read data
        df = spark.read.jdbc(url=DB_URL, table="stay_location_data", properties=DB_PROPERTIES)

        # Step 1: Identify users with "stayed_at_place" records (potential home locations)
        logger.info("Identifying users with home locations...")
        users_with_home = df.filter(col("place_visit_status") == "stayed_at_place") \
                           .select("user_id").distinct()

        # Collect user_ids only once to avoid multiple actions
        user_ids_with_home = [row.user_id for row in users_with_home.collect()]

        # Step 2: Filter logic - exclude "other_location" records for users who have home locations
        logger.info("Filtering data...")
        df_filtered = df.filter(
            ~(col("user_id").isin(user_ids_with_home) &
              (col("place_visit_status") == "other_location"))
        )

        # Group by h3_cell_id_7 and calculate metrics
        logger.info("Calculating location metrics...")
        grouped = df_filtered.groupBy("h3_cell_id_7").agg(
            mean("latitude").alias("latitude"),
            mean("longitude").alias("longitude"),
            countDistinct("user_id").alias("unique_users"),
            count("user_id").alias("stay_events"),
            spark_sum(when(col("place_visit_status") == "stayed_at_place", 1).otherwise(0)).alias("lived_in_place"),
            mean("stay_hours").alias("avg_stay_hours")
        )

        # Add derived columns
        grouped = grouped.withColumn("location_score", col("unique_users") * 0.66) \
                         .withColumn("lived_in_place", (col("lived_in_place") > 0).cast("integer")) \
                         .withColumnRenamed("h3_cell_id_7", "h3_id") \
                         .orderBy("h3_id")

        logger.info("Sample of processed data:")
        grouped.show(5)

        # Write to database
        logger.info("Writing results to h3_unique_count table...")
        grouped.write.jdbc(
            url=DB_URL,
            table="h3_unique_count",
            mode='append',  # Consider 'overwrite' if needed
            properties=DB_PROPERTIES
        )

        logger.info("Data successfully processed and inserted into h3_unique_count.")
        return grouped

    except Exception as e:
        logger.error(f"Error processing stay locations: {str(e)}")
        raise
    finally:
        if spark:
            spark.stop()
