from config.sparkConfig import SparkConnection, DB_URL, DB_PROPERTIES

def get_data_by_date(target_date):
    spark = SparkConnection()
    if spark is None:
        print("❌ Failed to establish Spark connection")
        return None

    query = f"(SELECT date, h3_cell_id, mobile_number, start_time, end_time, h3_cell_id_7, latitude, longitude, stay_duration, user_id FROM od_matrix WHERE date = '{target_date}') AS temp"

    try:
        df_filtered = spark.read.jdbc(DB_URL, query, properties=DB_PROPERTIES)
        print(f"✅ Successfully fetched data for date: {target_date}")
        return df_filtered
    except Exception as e:
        print(f"❌ Error processing data: {str(e)}")
        return None

