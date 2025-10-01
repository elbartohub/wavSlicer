from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os
import json
from werkzeug.utils import secure_filename
from audio_splitter import AudioSplitter
import zipfile
import tempfile
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'input'
app.config['OUTPUT_FOLDER'] = 'output'

# Initialize audio splitter
splitter = AudioSplitter()

# Store processing status
processing_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'wav'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only WAV files are allowed'}), 400
        
        # Get parameters
        max_duration = float(request.form.get('max_duration', 60))
        min_silence_len = int(request.form.get('min_silence_len', 1000))
        silence_thresh = int(request.form.get('silence_thresh', -40))
        
        # Validate parameters
        if max_duration <= 0 or max_duration > 3600:  # Max 1 hour per segment
            return jsonify({'error': 'Duration must be between 1 and 3600 seconds'}), 400
        
        if min_silence_len < 100 or min_silence_len > 5000:
            return jsonify({'error': 'Minimum silence length must be between 100 and 5000 ms'}), 400
        
        if silence_thresh < -80 or silence_thresh > 0:
            return jsonify({'error': 'Silence threshold must be between -80 and 0 dB'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Get audio info
        try:
            audio_info = splitter.get_audio_info(filepath)
        except Exception as e:
            os.remove(filepath)  # Clean up
            return jsonify({'error': f'Invalid audio file: {str(e)}'}), 400
        
        # Store processing job
        job_id = f"{timestamp}_{secure_filename(file.filename.rsplit('.', 1)[0])}"
        processing_status[job_id] = {
            'status': 'uploaded',
            'filename': filename,
            'filepath': filepath,
            'audio_info': audio_info,
            'parameters': {
                'max_duration': max_duration,
                'min_silence_len': min_silence_len,
                'silence_thresh': silence_thresh
            },
            'output_files': [],
            'error': None
        }
        
        return jsonify({
            'job_id': job_id,
            'audio_info': audio_info,
            'message': 'File uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/process/<job_id>', methods=['POST'])
def process_audio(job_id):
    try:
        if job_id not in processing_status:
            return jsonify({'error': 'Job not found'}), 404
        
        job = processing_status[job_id]
        if job['status'] != 'uploaded':
            return jsonify({'error': 'Job already processed or in progress'}), 400
        
        # Update status
        job['status'] = 'processing'
        
        # Clear output folder before processing
        splitter.clear_output_folder()
        
        # Process the audio file
        try:
            output_files = splitter.detect_silence_and_split(
                job['filepath'],
                job['parameters']['max_duration'],
                job['parameters']['min_silence_len'],
                job['parameters']['silence_thresh']
            )
            
            job['output_files'] = [os.path.basename(f) for f in output_files]
            job['status'] = 'completed'
            
            return jsonify({
                'status': 'completed',
                'output_files': job['output_files'],
                'total_segments': len(output_files)
            })
            
        except Exception as e:
            job['status'] = 'error'
            job['error'] = str(e)
            return jsonify({'error': f'Processing failed: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/status/<job_id>')
def get_status(job_id):
    if job_id not in processing_status:
        return jsonify({'error': 'Job not found'}), 404
    
    job = processing_status[job_id]
    return jsonify({
        'status': job['status'],
        'output_files': job.get('output_files', []),
        'error': job.get('error'),
        'audio_info': job.get('audio_info')
    })

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(
            os.path.join(app.config['OUTPUT_FOLDER'], filename),
            as_attachment=True
        )
    except Exception as e:
        return jsonify({'error': f'File not found: {str(e)}'}), 404

@app.route('/download_all/<job_id>')
def download_all(job_id):
    try:
        if job_id not in processing_status:
            return jsonify({'error': 'Job not found'}), 404
        
        job = processing_status[job_id]
        if job['status'] != 'completed':
            return jsonify({'error': 'Job not completed'}), 400
        
        # Create a temporary zip file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
            for filename in job['output_files']:
                file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
                if os.path.exists(file_path):
                    zipf.write(file_path, filename)
        
        return send_file(
            temp_zip.name,
            as_attachment=True,
            download_name=f"{job_id}_split_audio.zip",
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/clear')
def clear_files():
    try:
        # Clear output folder
        splitter.clear_output_folder()
        
        # Clear input folder
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # Clear processing status
        processing_status.clear()
        
        return jsonify({'message': 'All files cleared successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Clear failed: {str(e)}'}), 500

if __name__ == '__main__':
    # Ensure folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)