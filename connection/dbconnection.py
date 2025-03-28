import psycopg2

def connect_to_db():
    """Establishes a connection to the PostgreSQL database."""
    try:
        # Database connection parameters
        db_params = {
            "dbname": "geo_od_metix",
            "user": "postgres",
            "password": "1111",
            "host": "localhost",
            "port": "5432"
        }

        # Connect to PostgreSQL
        conn = psycopg2.connect(**db_params)
        print("✅ Connected to the database successfully!")

        return conn  # Return the connection object

    except psycopg2.Error as e:
        print(f"❌ Error connecting to the database: {e}")
        return None

