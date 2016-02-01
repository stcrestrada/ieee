# IEEE data pull

### Setup

    sudo pip install inenv
    inenv init ieee

    # Create local psql database
    psql
    CREATE DATABASE ieee;

### Usage

#### Run Celery Workers

    # Start the workers in one process
    inenv ieee # Activate your virtualenv
    python manage.py celery worker -c 8 # 8 concurrent processes for local dev


#### Pull data
 
    # Begin pulling data in another process/session
    python manage.py shell
    from apps.scraper.tasks import *

    # To scrape a single year
    scrape_year.apply_async([2010])

    # To scrap all years/data
    scrape_all.apply_async()
