# WAV Audio Splitter

A web-based application that automatically splits long WAV audio files into smaller segments based on silence detection, with configurable duration limits.

## Features

- **Silence Detection**: Automatically detects silence in audio files to find optimal split points
- **Duration Limits**: Set maximum duration for each audio segment
- **Web Interface**: Easy-to-use web interface for file upload and parameter configuration
- **Batch Download**: Download all split files as a ZIP archive
- **Audio Analysis**: View detailed information about uploaded audio files
- **Drag & Drop**: Convenient drag-and-drop file upload

## Requirements

- Python 3.7 or higher
- FFmpeg (for audio processing)

## Installation

1. **Clone or download this project**

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**:
   - **Windows**: Download from https://ffmpeg.org/download.html and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg` (Ubuntu/Debian) or `sudo yum install ffmpeg` (CentOS/RHEL)

## Usage

1. **Start the application**:
   ```bash
   python app.py
   ```

2. **Open your web browser** and navigate to:
   ```
   http://localhost:5000
   ```

3. **Upload and process your WAV file**:
   - Click "Click to select a WAV file" or drag and drop a WAV file
   - Configure the splitting parameters:
     - **Maximum Duration**: Maximum length for each segment (1-3600 seconds)
     - **Minimum Silence Length**: Minimum silence duration to consider as split point (100-5000 ms)
     - **Silence Threshold**: Audio level below which is considered silence (-80 to 0 dB)
   - Click "Upload & Process"

4. **Download the results**:
   - Download individual files or all files as a ZIP archive
   - Files are automatically named with sequential numbers

## Parameters Explanation

### Maximum Duration (seconds)
- Sets the maximum length for each audio segment
- If a segment would be longer than this duration, it will be split even if no silence is detected
- Range: 1-3600 seconds (1 second to 1 hour)

### Minimum Silence Length (milliseconds)
- The minimum duration of silence required to consider it as a potential split point
- Shorter silences will be ignored
- Range: 100-5000 ms

### Silence Threshold (dB)
- The audio level below which sound is considered "silence"
- Lower values (more negative) mean quieter sounds are still considered as audio
- Higher values (less negative) mean louder sounds are considered as silence
- Range: -80 to 0 dB
- Typical values: -40 dB for normal speech, -60 dB for quiet recordings

## File Structure

```
wavSlice/
├── app.py                 # Flask web application
├── audio_splitter.py      # Audio processing logic
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── input/                # Uploaded WAV files (auto-created)
├── output/               # Split audio files (auto-created)
└── templates/
    └── index.html        # Web interface
```

## How It Works

1. **Upload**: WAV files are uploaded to the `input/` folder
2. **Analysis**: The application analyzes the audio to detect silence periods
3. **Splitting**: The audio is split at silence points, respecting the maximum duration limit
4. **Output**: Split files are saved to the `output/` folder with sequential naming

## Algorithm Details

The splitting algorithm works in two phases:

1. **Silence-based splitting**: Uses pydub's silence detection to find natural break points
2. **Duration-based splitting**: If segments are still too long, splits them at the best available silence point near the duration limit

This ensures that:
- Audio is split at natural pauses when possible
- No segment exceeds the specified maximum duration
- Speech and music are not cut off abruptly when avoidable

## Troubleshooting

### "FFmpeg not found" error
- Make sure FFmpeg is installed and added to your system PATH
- Restart your terminal/command prompt after installing FFmpeg

### "File format not supported" error
- Ensure your file is a valid WAV format
- Try converting your audio file to WAV using an audio converter

### Large file upload issues
- The application supports files up to 500MB
- For larger files, consider pre-processing them or increasing the limit in `app.py`

### Memory issues with very long files
- Try reducing the maximum duration parameter
- Close other applications to free up memory
- Consider splitting very large files manually first

## License

This project is open source and available under the MIT License.