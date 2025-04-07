import pandas as pd
from skmob import TrajDataFrame
from skmob.measures.individual import home_location
import logging
from time import time
import h3

from config.sparkConnection import get_data_by_date

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_home_locations(df, min_night, s_time , e_time):
    """Calculate home locations with timing measurements and logging."""

    """min_hours: Minimum cumulative hours spent at location to consider it home"""

    # Convert Spark DataFrame to Pandas
    start_time = time()
    pdf = df.toPandas()
    logger.info(f"Data conversion to Pandas completed in {time() - start_time:.2f} seconds")

    # Convert to proper datetime
    start_time = time()
    pdf['datetime'] = pd.to_datetime(pdf['date']) + pd.to_timedelta(pdf['start_time'], unit='m')
    logger.info(f"Datetime conversion completed in {time() - start_time:.2f} seconds")

    # Create TrajDataFrame
    start_time = time()
    tdf = TrajDataFrame(pdf,
                        latitude='latitude',
                        longitude='longitude',
                        datetime='datetime',
                        user_id='user_id')
    logger.info(f"TrajDataFrame creation completed in {time() - start_time:.2f} seconds")

    # Get home locations
    start_time = time()
    home_origin = home_location(tdf, s_time, e_time, min_night)
    # afternoon_location = home_location(tdf, '7:01', '21:59')

    # logger.info(f'this is an after night data of person {afternoon_location}')

    logger.info(f"Home location calculation completed in {time() - start_time:.2f} seconds")

    # Convert to regular DataFrame and filter home points
    start_time = time()
    pdf = pd.DataFrame(tdf)
    home_points = pdf.merge(home_origin, on='uid', suffixes=('', '_home'))
    home_points = home_points[
        (home_points['lat'] == home_points['lat_home']) &
        (home_points['lng'] == home_points['lng_home'])
        ]

    # Calculate first detection time
    first_detection = home_points.groupby('uid')['datetime'].min().reset_index()
    first_detection.columns = ['uid', 'first_detection_time']
    logger.info(f"Home point analysis completed in {time() - start_time:.2f} seconds")

    # Add H3 cells and merge results
    start_time = time()
    home_origin['h3_cell'] = home_origin.apply(
        lambda row: h3.geo_to_h3(row['lat'], row['lng'], 12), axis=1
    )

    result = home_origin.merge(first_detection, on='uid')
    result['night_time_range'] = '22:00-07:00'

    final_result = result.rename(columns={
        'lat': 'home_lat',
        'lng': 'home_lng'
    })[[
        'uid',
        'home_lat',
        'home_lng',
        'h3_cell',
        'night_time_range',
        'first_detection_time',
    ]]
    logger.info(f"Final result preparation completed in {time() - start_time:.2f} seconds")

    return final_result


if __name__ == "__main__":
    date = "2025-03-25"
    data = get_data_by_date(date)
    result = calculate_home_locations(data, 6, "22:00", "07:00")
    print("\nFinal Result:")
    print(result)