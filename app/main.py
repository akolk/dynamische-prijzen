import requests
import time
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Float, TIMESTAMP, func
from sqlalchemy.orm import declarative_base, sessionmaker, close_all_sessions
import pandas as pd

def main():
    # Environment variables configuration
    db_host = os.environ.get("DB_HOST", "xxx.pg.host.com")
    db_port = int(os.environ.get("DB_PORT", 12164))
    db_name = os.environ.get("DB_NAME", "dynamischetarieven")
    db_user = os.environ.get("DB_USER", "user")
    db_password = os.environ.get("DB_PASSWORD", "password")

    # Construct connection string
    db_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require"

    table_name = "dynamische_tarieven"
    base_url = "https://api.eerlijkverbruik.nl/chart_stroom"

    print(f"Connecting to database {db_name} at {db_host}:{db_port}...")

    # Close any existing sessions
    close_all_sessions()

    # Define the database engine
    try:
        engine = create_engine(db_url, echo=False)
    except Exception as e:
        print(f"Failed to create engine: {e}")
        sys.exit(1)

    # Define the base class
    Base = declarative_base()

    # Define the table
    class DynamischeTarieven(Base):
        __tablename__ = table_name
        uur = Column(TIMESTAMP, primary_key=True, nullable=False)
        prijs = Column(Float, nullable=False)

    # Create the table if it doesn't exist
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        print(f"Failed to create table: {e}")
        sys.exit(1)

    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Default start date
        start_date = datetime.strptime("2022-01-01", "%Y-%m-%d")

        # Find the max value for the 'uur' column to resume from
        max_uur = session.query(func.max(DynamischeTarieven.uur)).scalar()
        print(f"Last record date in DB: {max_uur}")

        if max_uur is not None:
            # Resume from the next day
            start_date = max_uur + timedelta(days=1)

        # End date (tomorrow midnight)
        end_date = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        print(f"Fetching data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            print(f"Processing date: {date_str}")

            params = { "date": date_str, "company": "" }

            try:
                response = requests.get(base_url, params=params)

                if response.status_code == 200:
                    prijzen = response.json()
                    if prijzen:
                        for uur in prijzen:
                            # uur[0] is ms timestamp, uur[1] is price
                            dt_object = datetime.fromtimestamp(uur[0]/1000)

                            # Using merge to avoid Primary Key violations if re-running
                            new_record = DynamischeTarieven(uur=dt_object, prijs=uur[1])
                            session.merge(new_record)

                        session.commit()
                        # print(f"Success for {date_str}")
                    else:
                         print(f"No data found for {date_str}")

                else:
                    print(f"Error {response.status_code} for {date_str}: {response.text}")

            except Exception as e:
                print(f"Exception processing {date_str}: {e}")
                session.rollback()

            # Sleep to be polite to the API
            time.sleep(1)
            current_date += timedelta(days=1)

    except Exception as e:
        print(f"An error occurred during execution: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()
