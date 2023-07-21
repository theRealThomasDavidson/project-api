from app import create_app, db
from flask_migrate import Migrate
import ssl

app = create_app()
if __name__ == '__main__':
    migrate = Migrate(app, db)
    app.run(host='0.0.0.0', port=5001)
