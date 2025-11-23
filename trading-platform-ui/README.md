Install required dependencies:

`pip install flask flask-sqlalchemy flask-migrate python-dotenv psycopg2-binary`

Initialize the database and migrations:

bash# Initialize migrations (run once)
`flask db init`

# Create first migration
`flask db migrate -m "Initial transaction table"`

# Apply migration to database
`flask db upgrade`

Populate with sample data:

`python populate_db.py`

Run the application:
`python app.py`

Visit http://localhost:5000 to see your transactions dashboard.
