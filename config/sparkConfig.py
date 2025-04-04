from pyspark.sql import SparkSession

DB_URL = "jdbc:postgresql://localhost:5432/geo_od_metix"  # ✅ Updated with actual DB details
DB_PROPERTIES = {
    "user": "postgres",
    "password": "1111",
    "driver": "org.postgresql.Driver"
}

def SparkConnection():
    return SparkSession.builder \
        .appName("PostgresDataFilter") \
        .config("spark.jars", "/home/lg/PycharmProjects/geo_pluse/resources/postgresql-42.5.4.jar") \
        .getOrCreate()

