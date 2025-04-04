import logging

from config.sparkConfig import SparkConnection, DB_URL, DB_PROPERTIES
from config.sparkConnection import get_data_by_date
from originFinder.origin import identify_stay_locations_spark
from mapView.OD_mateix_slm import process_stay_locations

if __name__ == "__main__":
    date_to_get = "2025-03-25"
    jdbc_url = DB_URL  # Replace with your actual JDBC URL
    table_name = "stay_location_data"
    filtered_data = get_data_by_date(date_to_get)

    if filtered_data:
        spark = SparkConnection()
        stay_locations_df = identify_stay_locations_spark(filtered_data)
        stay_locations_df.show(10)
        stay_locations_df.write.jdbc(url=jdbc_url, table=table_name, mode='append', properties=DB_PROPERTIES)
        logging.info("Data successfully inserted into stay_location_data.")

        logging.basicConfig(level=logging.INFO)
        results = process_stay_locations()
        spark.stop()