from flask import Flask, send_file, jsonify, request, render_template
from PIL import Image
from models import load_models, generate_image_from_prompt
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from pathlib import Path
import threading
base, refiner = load_models()
running = False

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///images.db'

db = SQLAlchemy(app)
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255), unique=True)
    prompt = db.Column(db.String(4096), unique=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, image_path, prompt):
        self.image_path = image_path
        self.prompt = prompt

def process(prompt, image_paths):
    global running
    running = True
    for path in image_paths:
        image = generate_image_from_prompt(base, refiner, prompt)
        image.save(path)
    running = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_job', methods=['POST'])
def start_job():
    prompt = request.json.get('prompt', None)
    num_images = request.json.get('num_images', 1)
    if not prompt:
        return jsonify({'error': 'No input provided'}), 400
    if running:
        return jsonify({'error': 'Already running'}), 400

    # Save the image hash and prompt to the database
    root_path = Path("/mnt/nas/images")
    image_name = datetime.now().strftime("%Y%m%d%H%M%S%f") + ".png"
    image_paths = []
    for i in range(int(num_images)):
        image_name = str(i) + "_" + image_name
        image_path = root_path / image_name
        image = Image(str(image_path), prompt)
        db.session.add(image)
        db.session.commit()
        image_paths.append(image_path)

    thread = threading.Thread(target=process, args=(prompt,image_paths,))
    thread.start()

    return jsonify({'status': 'queued'}), 202

@app.route('/get_image/<image_id>', methods=['GET'])
def get_image(image_id):
    # Pull from the database based on the image hash
    image = Image.query.filter_by(id=image_id).first()
    image_path = image.image_path

    # Return the image
    return send_file(image_path, mimetype='image/png')

@app.route('/get_prompt/<image_id>', methods=['GET'])
def get_prompt(image_id):
    # Pull from the database based on the image hash
    image = Image.query.filter_by(id=image_id).first()
    prompt = image.prompt

    # Return the prompt
    return jsonify({'prompt': prompt}), 200

@app.route('/get_ids/timeframe', methods=['POST'])
def timeframe():
    # get image ids from database based on timeframe
    oldest = request.json.get('oldest', datetime.min)
    newest = request.json.get('newest', datetime.now())
    entries = Image.query.filter(Image.timestamp >= oldest).filter(Image.timestamp <= newest).all()
    ids = [entry.id for entry in entries]
    return jsonify({'entries': ids}), 200

@app.route('/get_ids/prompt', methods=['POST'])
def prompt():
    # Search database for prompts containing the search string
    search_string = request.json.get('search_string', '')
    entries = Image.query.filter(Image.prompt.contains(search_string)).all()
    ids = [entry.id for entry in entries]
    return jsonify({'entries': ids}), 200

@app.route('/del_image/<image_id>', methods=['DELETE'])
def del_image(image_id):
    # Delete image from database and filesystem
    image = Image.query.filter_by(id=image_id).first()
    image_path = image.image_path
    db.session.delete(image)
    db.session.commit()
    Path(image_path).unlink()
    return jsonify({'status': 'deleted'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='192.168.69.4')
