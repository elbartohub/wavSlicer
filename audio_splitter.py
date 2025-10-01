import os
from pydub import AudioSegment
from pydub.silence import split_on_silence
import math

class AudioSplitter:
    def __init__(self, input_folder="input", output_folder="output"):
        self.input_folder = input_folder
        self.output_folder = output_folder
        
        # Create folders if they don't exist
        os.makedirs(self.input_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
    
    def detect_silence_and_split(self, audio_file_path, max_duration_seconds=60, 
                                min_silence_len=1000, silence_thresh=-40):
        """
        Split audio file based on silence detection with duration limits
        
        Args:
            audio_file_path: Path to the input WAV file
            max_duration_seconds: Maximum duration for each split (in seconds)
            min_silence_len: Minimum length of silence to be considered a split point (ms)
            silence_thresh: Silence threshold in dB
        
        Returns:
            List of output file paths
        """
        try:
            # Load audio file
            if not os.path.exists(audio_file_path):
                raise Exception(f"Audio file not found: {audio_file_path}")
            
            audio = AudioSegment.from_wav(audio_file_path)
            
            if len(audio) == 0:
                raise Exception("Audio file is empty or corrupted")
            
            # Get base filename without extension
            base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
            
            # Convert max duration to milliseconds
            max_duration_ms = max_duration_seconds * 1000
            
            # Check if audio is shorter than or equal to the requested duration
            audio_duration_ms = len(audio)
            if audio_duration_ms <= max_duration_ms:
                # Audio is already shorter than requested duration, return as single chunk
                chunks = [audio]
            else:
                # For longer audio, prioritize duration-based splitting to get chunks close to target duration
                chunks = self._split_by_duration_and_silence(audio, max_duration_ms, 
                                                           min_silence_len, silence_thresh)
            
            # Ensure we have chunks to process
            if not chunks:
                # If no chunks were created, create one chunk with the entire audio
                chunks = [audio]
            
            # Save chunks
            output_files = []
            for i, chunk in enumerate(chunks):
                if len(chunk) > 0:  # Only save non-empty chunks
                    output_filename = f"{base_name}_part_{i+1:03d}.wav"
                    output_path = os.path.join(self.output_folder, output_filename)
                    try:
                        chunk.export(output_path, format="wav")
                        output_files.append(output_path)
                    except Exception as export_error:
                        raise Exception(f"Failed to export chunk {i+1}: {str(export_error)}")
            
            if not output_files:
                raise Exception("No audio segments were generated")
            
            return output_files
            
        except Exception as e:
            raise Exception(f"Error processing audio file: {str(e)}")
    
    def _split_by_duration_and_silence(self, audio, max_duration_ms, min_silence_len, silence_thresh):
        """
        Split audio to get chunks as close as possible to max_duration_ms,
        preferring silence points near the target duration
        """
        chunks = []
        audio_length = len(audio)
        
        start = 0
        while start < audio_length:
            # Calculate the target end point (aim for max duration)
            target_end = start + max_duration_ms
            
            # If this would be the last chunk, just take what's left
            if target_end >= audio_length:
                chunks.append(audio[start:])
                break
            
            # Define search window around target point (±2 seconds)
            search_window = min(2000, max_duration_ms // 4)  # 2 seconds or 1/4 of max duration
            search_start = max(start + max_duration_ms - search_window, start + max_duration_ms // 2)
            search_end = min(target_end + search_window, audio_length)
            
            # Find the best silence point in the search window
            best_split = self._find_best_silence_point_near_target(
                audio[search_start:search_end], 
                silence_thresh, 
                min_silence_len,
                target_end - search_start  # Target position within search segment
            )
            
            if best_split is not None:
                actual_end = search_start + best_split
            else:
                # No silence found, split at target duration
                actual_end = target_end
            
            chunks.append(audio[start:actual_end])
            start = actual_end
        
        return chunks
    
    def _find_best_silence_point_near_target(self, audio_segment, silence_thresh, min_silence_len, target_position):
        """
        Find the best silence point closest to the target position within the audio segment
        """
        if len(audio_segment) < min_silence_len:
            return None
        
        # Find all silence ranges
        silence_ranges = []
        chunk_size = 100  # Check every 100ms
        
        for i in range(0, len(audio_segment) - min_silence_len, chunk_size):
            chunk = audio_segment[i:i + min_silence_len]
            try:
                if chunk.dBFS < silence_thresh or chunk.dBFS == float('-inf'):
                    # Found potential silence, extend it
                    silence_start = i
                    silence_end = i + min_silence_len
                    
                    # Extend backwards
                    while silence_start > 0:
                        test_chunk = audio_segment[silence_start - chunk_size:silence_start + min_silence_len]
                        if len(test_chunk) >= min_silence_len and (test_chunk.dBFS < silence_thresh or test_chunk.dBFS == float('-inf')):
                            silence_start -= chunk_size
                        else:
                            break
                    
                    # Extend forwards
                    while silence_end < len(audio_segment) - min_silence_len:
                        test_chunk = audio_segment[silence_end - min_silence_len:silence_end + chunk_size]
                        if len(test_chunk) >= min_silence_len and (test_chunk.dBFS < silence_thresh or test_chunk.dBFS == float('-inf')):
                            silence_end += chunk_size
                        else:
                            break
                    
                    # Avoid overlapping ranges
                    if not any(silence_start < end and silence_end > start for start, end in silence_ranges):
                        silence_ranges.append((silence_start, silence_end))
            except:
                continue
        
        if not silence_ranges:
            return None
        
        # Find the silence point closest to target position
        best_split = None
        best_distance = float('inf')
        
        for start, end in silence_ranges:
            # Use middle of silence range
            silence_middle = (start + end) // 2
            distance = abs(silence_middle - target_position)
            
            if distance < best_distance:
                best_distance = distance
                best_split = silence_middle
        
        return best_split
    
    def _find_best_silence_point(self, audio_segment, silence_thresh, min_silence_len):
        """
        Find the best silence point in an audio segment using pydub's built-in methods
        """
        # Use pydub's silence detection to find silence periods
        silence_ranges = []
        
        # Split the segment into smaller chunks to analyze
        chunk_length = min_silence_len  # Use minimum silence length as chunk size
        
        for i in range(0, len(audio_segment), chunk_length // 4):  # Overlap chunks
            chunk_end = min(i + chunk_length, len(audio_segment))
            chunk = audio_segment[i:chunk_end]
            
            # Check if this chunk is mostly silent
            if len(chunk) >= min_silence_len:
                try:
                    # Use pydub's dBFS (decibels relative to full scale)
                    chunk_db = chunk.dBFS
                    # Handle -inf case (completely silent audio)
                    if chunk_db == float('-inf') or chunk_db < silence_thresh:
                        silence_ranges.append((i, chunk_end))
                except:
                    # If dBFS calculation fails, skip this chunk
                    continue
        
        # Find the longest silence period
        if silence_ranges:
            # Merge overlapping ranges and find the longest
            merged_ranges = []
            current_start, current_end = silence_ranges[0]
            
            for start, end in silence_ranges[1:]:
                if start <= current_end + min_silence_len // 2:  # Allow small gaps
                    current_end = max(current_end, end)
                else:
                    merged_ranges.append((current_start, current_end))
                    current_start, current_end = start, end
            
            merged_ranges.append((current_start, current_end))
            
            # Find the longest silence
            longest_silence = max(merged_ranges, key=lambda x: x[1] - x[0])
            
            # Return the middle point of the longest silence
            return (longest_silence[0] + longest_silence[1]) // 2
        
        return None
    
    def get_audio_info(self, audio_file_path):
        """
        Get basic information about the audio file
        """
        try:
            audio = AudioSegment.from_wav(audio_file_path)
            return {
                'duration_seconds': len(audio) / 1000,
                'channels': audio.channels,
                'frame_rate': audio.frame_rate,
                'sample_width': audio.sample_width
            }
        except Exception as e:
            raise Exception(f"Error reading audio file info: {str(e)}")
    
    def clear_output_folder(self):
        """
        Clear all files in the output folder
        """
        for filename in os.listdir(self.output_folder):
            file_path = os.path.join(self.output_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)