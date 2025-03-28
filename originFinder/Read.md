# Documentation: Identifying Primary Stay Locations using PySpark

## Overview
This script processes user stay data to identify primary stay locations based on various factors, such as stay duration, time of visit, and geographical proximity. It applies filtering, clustering, and probability models to enhance accuracy in determining key locations (e.g., home or frequently visited places).

## Key Features
- Converts stay duration from minutes to hours.
- Identifies overnight stays (between 12 AM - 6 AM).
- Determines the longest stay per user.
- Filters valid stay locations based on duration.
- Resolves multiple stay locations by clustering and ranking.
- Implements geographical clustering using H3 cell-based refinement.
- Assigns visit status for a specific place (stay, pass-through, or other location).
- Applies a probability model to detect home locations.
- Labels users as frequent movers or stable based on movement patterns.
- Handles cases where users have identical stay durations by selecting the earliest arrival.

---

## Step-by-Step Breakdown

### 1. Convert Stay Duration to Hours
The script converts the `stay_duration` from minutes to hours for easier processing:
```python
spark_df = spark_df.withColumn('stay_hours', (F.col('stay_duration') / 60).cast('double'))
```

### 2. Identify Overnight Stays
Overnight stays are defined as stays starting between 12 AM and 6 AM and lasting at least 6 hours:
```python
spark_df = spark_df.withColumn(
    'overnight_stay',
    F.when((F.hour('start_time') < 6) & (F.col('stay_hours') >= 6), 'yes').otherwise('no')
)
```

### 3. Determine the Longest Stay per User
A window function partitions data by `user_id` and identifies the maximum stay duration:
```python
user_window = Window.partitionBy('user_id')
spark_df = spark_df.withColumn('max_stay', F.max('stay_hours').over(user_window))
```

### 4. Filter Primary Stay Locations
- Locations with at least 6 hours of stay are retained.
- If no such location exists, the longest stay location is used.
```python
stay_locations = spark_df.filter(F.col('stay_hours') >= 6)
fallback_locations = spark_df.filter((F.col('stay_hours') == F.col('max_stay')) & (F.col('stay_hours') < 6))
all_locations = stay_locations.unionByName(fallback_locations)
```

### 5. Resolve Multiple Stay Locations
Users with multiple locations are identified and handled separately:
```python
multi_loc_users = all_locations.groupBy('user_id').agg(F.count('*').alias('location_count'))
multi_loc_users = multi_loc_users.filter(F.col('location_count') > 1).select('user_id')
single_loc_users = all_locations.join(multi_loc_users, 'user_id', 'left_anti')
```

### 6. Cluster Stay Locations by H3 Cell ID
Users with multiple locations are clustered based on `h3_cell_id_7`, and the most relevant stay is selected:
```python
clustering_window = Window.partitionBy('user_id', 'h3_cell_id_7').orderBy(F.desc('stay_hours'), F.asc('start_time'))
clustered_df = all_locations.join(multi_loc_users, 'user_id')
clustered_df = clustered_df.withColumn('rank', F.rank().over(clustering_window))
primary_stay_locations = clustered_df.filter(F.col('rank') == 1).drop('rank')
```

### 7. Apply Geographical Clustering (H3-based Refinement)
A window function is used to track previous latitude and longitude for each user:
```python
geo_window = Window.partitionBy('user_id').orderBy(F.asc('start_time'))
final_df = final_df.withColumn("previous_lat", F.lag("latitude").over(geo_window))
final_df = final_df.withColumn("previous_lon", F.lag("longitude").over(geo_window))
```
A UDF is used to check if two locations are within 200m:
```python
def is_nearby(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return False
    return geodesic((lat1, lon1), (lat2, lon2)).meters < 200

nearby_udf = F.udf(lambda lat1, lon1, lat2, lon2: is_nearby(lat1, lon1, lat2, lon2))
final_df = final_df.withColumn("nearby_status",
    nearby_udf(F.col("latitude"), F.col("longitude"), F.col("previous_lat"), F.col("previous_lon"))
)
```

### 8. Determine Place Visit Status
A fixed place (`PLACE_LAT`, `PLACE_LON`) is used to check whether a user stayed, passed through, or was at another location:
```python
final_df = final_df.withColumn(
    "place_visit_status",
    F.when((F.col("latitude") == PLACE_LAT) & (F.col("longitude") == PLACE_LON) & (F.col("stay_hours") >= 6), "stayed_at_place")
    .when((F.col("latitude") == PLACE_LAT) & (F.col("longitude") == PLACE_LON) & (F.col("stay_hours") < 6), "passed_through_place")
    .otherwise("other_location")
)
```

### 9. Probability Model for Home Detection
Probability-based home detection:
```python
final_df = final_df.withColumn(
    "home_probability",
    F.when(F.col("overnight_stay") == "yes", 0.7)
    .when(F.col("stay_hours") == F.col("max_stay"), 0.3)
    .otherwise(0.0)
)
```

### 10. Identify Frequent Movers
Users who frequently change locations (more than 3 distinct locations) are marked as `frequent_mover`:
```python
moving_users = spark_df.groupBy('user_id').agg(F.countDistinct('h3_cell_id').alias('distinct_locations'))
moving_users = moving_users.filter(F.col('distinct_locations') > 3)
final_df = final_df.join(moving_users, 'user_id', 'left')
final_df = final_df.withColumn("movement_status",
    F.when(F.col("distinct_locations").isNotNull(), "frequent_mover").otherwise("stable")
).drop("distinct_locations")
```

### 11. Handle Equal Stay Durations (Choose Earliest Arrival)
Users with identical stay durations are resolved by selecting the earliest recorded stay:
```python
equal_stay_users = clustered_df.groupBy("user_id").agg(F.countDistinct("stay_hours").alias("stay_variants"))
equal_stay_users = equal_stay_users.filter(F.col("stay_variants") == 1).select("user_id")
clustered_df = clustered_df.join(equal_stay_users, "user_id", "inner")
clustered_df = clustered_df.withColumn("earliest_rank", F.rank().over(Window.partitionBy("user_id").orderBy("start_time")))
earliest_stay = clustered_df.filter(F.col("earliest_rank") == 1).drop("earliest_rank")
```

---

## Final Output
The processed DataFrame contains columns such as:
- User stay details
- Movement status
- Home probability
- Nearby location status
- Place visit categorization

This refined approach enhances stay location detection by incorporating time-based, geographical, and probabilistic methods.

