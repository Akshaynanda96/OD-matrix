from pyspark.sql import functions as F
from pyspark.sql.types import BooleanType
from pyspark.sql.window import Window
from geopy.distance import geodesic

PLACE_LAT = 21.085453
PLACE_LON = 79.0686

def identify_stay_locations_spark(stay_location_data):
    """
    Identify primary stay locations for users with enhanced accuracy.
    """
    # Convert stay duration to hours
    stay_location_data = stay_location_data.withColumn('stay_hours', (F.col('stay_duration') / 60).cast('double'))

    # Convert start_time and end_time to timestamps
    stay_location_data = stay_location_data.withColumn(
        "start_time",
        F.expr("make_timestamp(year(current_date()), month(current_date()), day(current_date()), start_time / 60, start_time % 60, 0)")
    )
    stay_location_data = stay_location_data.withColumn(
        "end_time",
        F.expr("make_timestamp(year(current_date()), month(current_date()), day(current_date()), end_time / 60, end_time % 60, 0)")
    )

    # Identify overnight stays (12 AM - 6 AM)
    stay_location_data = stay_location_data.withColumn(
        'overnight_stay',
        F.when((F.col('start_time').substr(12, 2).cast('int') < 6) & (F.col('stay_hours') >= 6), 'yes').otherwise('no')
    )

    # Determine the longest stay location per user
    user_window = Window.partitionBy('user_id')
    stay_location_data = stay_location_data.withColumn('max_stay', F.max('stay_hours').over(user_window))

    # Filter stay locations (≥6 hours) or fallback to max stay per user
    stay_locations = stay_location_data.filter(F.col('stay_hours') >= 6)
    fallback_locations = stay_location_data.filter((F.col('stay_hours') == F.col('max_stay')) & (F.col('stay_hours') < 6))
    all_locations = stay_locations.unionByName(fallback_locations)

    # Resolve multiple stay locations
    multi_loc_users = all_locations.groupBy('user_id').agg(F.count('*').alias('location_count')).filter(F.col('location_count') > 1)
    single_loc_users = all_locations.join(multi_loc_users.select('user_id'), 'user_id', 'left_anti')

    # Cluster by h3_cell_id_7
    clustering_window = Window.partitionBy('user_id', 'h3_cell_id_7').orderBy(F.desc('stay_hours'), F.asc('start_time'))
    clustered_df = all_locations.join(multi_loc_users, 'user_id').withColumn('rank', F.rank().over(clustering_window))
    primary_stay_locations = clustered_df.filter(F.col('rank') == 1).drop('rank')

    # Merge single and clustered stay locations
    final_df = single_loc_users.unionByName(primary_stay_locations.select(single_loc_users.columns))

    # Geographical Clustering (H3-based Refinement)
    geo_window = Window.partitionBy('user_id').orderBy(F.asc('start_time'))
    final_df = final_df.withColumn("previous_lat", F.lag("latitude").over(geo_window))
    final_df = final_df.withColumn("previous_lon", F.lag("longitude").over(geo_window))

    def is_nearby(lat1, lon1, lat2, lon2):
        """Check if two locations are within 200m radius."""
        if None in (lat1, lon1, lat2, lon2):
            return False
        return geodesic((lat1, lon1), (lat2, lon2)).meters < 200

    # UDF for checking if nearby
    nearby_udf = F.udf(is_nearby, returnType=BooleanType())
    final_df = final_df.withColumn(
        "nearby_status",
        nearby_udf(F.col("latitude"), F.col("longitude"), F.col("previous_lat"), F.col("previous_lon"))
    )

    final_df = final_df.withColumn(
        "place_visit_status",
        F.when((F.col("latitude") == PLACE_LAT) & (F.col("longitude") == PLACE_LON) & (F.col("stay_hours") >= 6),
               "stayed_at_place")
        .when((F.col("latitude") == PLACE_LAT) & (F.col("longitude") == PLACE_LON) & (F.col("stay_hours") < 6),
              "passed_through_place")
        .otherwise("other_location")
    )

    # Probability Model for Home Detection
    final_df = final_df.withColumn(
        "home_probability",
        F.when(F.col("overnight_stay") == "yes", 0.7)
        .when(F.col("stay_hours") == F.col("max_stay"), 0.3)
        .otherwise(0.0)
    )

    # Identify Frequent Movers
    moving_users = stay_location_data.groupBy('user_id').agg(F.countDistinct('h3_cell_id').alias('distinct_locations'))
    moving_users = moving_users.filter(F.col('distinct_locations') > 3)
    final_df = final_df.join(moving_users, 'user_id', 'left')
    final_df = final_df.withColumn(
        "movement_status",
        F.when(F.col("distinct_locations").isNotNull(), "frequent_mover").otherwise("stable")
    ).drop("distinct_locations")

    # Equal Stay Durations (Choose Earliest Arrival)
    equal_stay_users = clustered_df.groupBy("user_id").agg(F.countDistinct("stay_hours").alias("stay_variants")).filter(F.col("stay_variants") == 1)
    clustered_df = clustered_df.join(equal_stay_users.select("user_id"), "user_id", "inner").withColumn(
        "earliest_rank", F.rank().over(Window.partitionBy("user_id").orderBy("start_time"))
    )
    earliest_stay = clustered_df.filter(F.col("earliest_rank") == 1).drop("earliest_rank")

    # Ensure earliest_stay has all required columns before union
    missing_cols = set(final_df.columns) - set(earliest_stay.columns)
    for col in missing_cols:
        earliest_stay = earliest_stay.withColumn(col, F.lit(None))

    final_df = final_df.unionByName(earliest_stay.select(final_df.columns))

    # Convert start_time and end_time to minutes
    final_df = final_df.withColumn("origin_start_time", (F.hour("start_time") * 60 + F.minute("start_time")).cast("int"))
    final_df = final_df.withColumn("origin_end_time", (F.hour("end_time") * 60 + F.minute("end_time")).cast("int"))

    return final_df