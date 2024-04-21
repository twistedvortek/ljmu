from flask import Flask, request, render_template, jsonify
from flask_restful import Api, Resource
from werkzeug.utils import secure_filename
from celery import Celery
import os
import time
from moviepy.editor import VideoFileClip
from flask_socketio import SocketIO, emit

app = Flask(__name__)
api = Api(app)  # Initialize Flask-RESTful
socketio = SocketIO(app)

# Configuration
UPLOAD_FOLDER = './uploads'
PROCESSED_FOLDER = './processed'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_duration(filepath, max_duration=30):
    video = VideoFileClip(filepath)
    duration = video.duration  # Duration in seconds
    video.close()
    return duration <= max_duration

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        if not allowed_duration(filepath):
            os.remove(filepath)  # Clean up by removing the uploaded file
            return jsonify({'error': 'Video duration exceeds the allowed limit.'}), 400

        task = process_file.apply_async(args=[filepath])
        return jsonify({'message': 'File uploaded. Processing started.', 'task_id': task.id})

@celery.task(bind=True)
def process_file(self, filepath):
    self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100, 'status': 'Starting'})
    # Example of process logic
    processed_output = yolo_deepsort_process(filepath)

    for i in range(1, 101):
        self.update_state(state='PROGRESS', meta={'current': i, 'total': 100, 'status': 'Processing'})
        time.sleep(0.1)  # Simulated processing delay

    processed_filepath = os.path.join(PROCESSED_FOLDER, os.path.basename(filepath))
    return {'current': 100, 'total': 100, 'status': 'Completed', 'processed_filepath': processed_filepath}

@socketio.on('connect')
def test_connect():
    emit('after connect',  {'data':'Connected'})

def yolo_deepsort_process(filepath):
    # Replace with your processing function
    return filepath  # Demo purpose

def gen_frames():
    cap = cv2.VideoCapture(0)  # or another video source
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

class UploadAPI(Resource):
    def post(self):
        response = upload_file()
        return response[0].get_json(), response[1]

api.add_resource(UploadAPI, '/api/upload')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    socketio.run(app, debug=True)