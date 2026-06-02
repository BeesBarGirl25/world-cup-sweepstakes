web: gunicorn app:app
release: python -c "from app import app, init_db; app.app_context().push(); init_db()"
