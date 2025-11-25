"""
Main application entry point for ResumeSense
Flask application with API routes and frontend serving.
"""
from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
import os
from backend.api.routes import api_bp
from backend.config import Config

# Create Flask app
app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_UPLOAD_SIZE

# ================================
# ADD THIS ROUTE (RUN ONCE)
# ================================
@app.route('/init-db')
def init_db_route():
    from backend.db.database import init_db
    init_db()
    return {"status": "Database tables created"}

# Enable CORS
CORS(app)
# Register API blueprint
app.register_blueprint(api_bp, url_prefix='/api')

# Ensure upload directory exists
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')


@app.route('/history')
def history_page():
    """Serve history page"""
    return render_template('history.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)


if __name__ == '__main__':
    # Run the application
    print("Starting ResumeSense application...")
    print(f"Upload folder: {Config.UPLOAD_FOLDER}")
    print(f"Database: {Config.MYSQL_DATABASE}")
    
    # Run in development mode
    app.run(debug=True, host='0.0.0.0', port=5001)

