
import os
import sys
import subprocess
import wave
import numpy as np
from PyQt6.QtWidgets import QApplication, QFileDialog

# Try to get ffmpeg path from imageio_ffmpeg
try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"Found FFmpeg at: {FFMPEG_EXE}")
except ImportError:
    print("Error: imageio_ffmpeg not found. Please install it.")
    sys.exit(1)

def main():
    app = QApplication(sys.argv)
    
    print("--- Select VIDEO File for Deep Inspection ---")
    video_path, _ = QFileDialog.getOpenFileName(None, "Select VIDEO File", "", "Video Files (*.mp4 *.avi *.mov *.mkv)")
    if not video_path:
        print("No file selected.")
        return

    print(f"\nTarget File: {video_path}")
    print("="*60)
    print("STEP 1: FFmpeg Probe (Stream Info)")
    print("="*60)
    
    # Run ffmpeg -i to get stream info (printed to stderr)
    cmd_probe = [FFMPEG_EXE, "-i", video_path]
    result = subprocess.run(cmd_probe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # FFmpeg prints file info to stderr
    print(result.stderr)
    
    print("\n" + "="*60)
    print("STEP 2: Raw Extraction Test (First 5s)")
    print("="*60)
    
    temp_wav = "debug_raw_audio.wav"
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
        
    # Command to extract first 5s to wav
    # -vn: no video
    # -acodec pcm_s16le: standard wav
    # -ar 44100: standard sample rate
    # -ac 1: force mono for easy check
    # -t 5: only 5 seconds
    cmd_extract = [
        FFMPEG_EXE, "-y", 
        "-i", video_path, 
        "-vn", 
        "-acodec", "pcm_s16le", 
        "-ar", "44100", 
        "-ac", "1", 
        "-t", "5", 
        temp_wav
    ]
    
    print(f"Running command: {' '.join(cmd_extract)}")
    extract_res = subprocess.run(cmd_extract, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if extract_res.returncode != 0:
        print("❌ FFmpeg Extraction Failed!")
        print(extract_res.stderr)
        return
    else:
        print("✅ FFmpeg Extraction Successful (Exit Code 0)")
        
    if not os.path.exists(temp_wav):
        print("❌ Error: Output file not created.")
        return
        
    print("\n" + "="*60)
    print("STEP 3: Analyzing Extracted Audio Data")
    print("="*60)
    
    try:
        with wave.open(temp_wav, 'rb') as wf:
            n_channels = wf.getnchannels()
            samp_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            
            print(f"Sample Rate: {sample_rate} Hz")
            print(f"Channels: {n_channels}")
            print(f"Sample Width: {samp_width} bytes")
            print(f"Frame Count: {n_frames}")
            
            # Read all frames
            raw_data = wf.readframes(n_frames)
            
            # Convert to numpy array (assuming pcm_s16le which is int16)
            if samp_width == 2:
                data = np.frombuffer(raw_data, dtype=np.int16)
            else:
                print(f"Unsupported sample width: {samp_width}")
                return

        # Convert to float for stats
        float_data = data.astype(np.float32)
        
        # Stats
        d_min = np.min(float_data)
        d_max = np.max(float_data)
        d_mean = np.mean(float_data)
        d_std = np.std(float_data)
        
        print(f"Min Value: {d_min}")
        print(f"Max Value: {d_max}")
        print(f"Mean Value: {d_mean:.4f}")
        print(f"Std Dev (Volume): {d_std:.4f}")
        
        print("\nFirst 10 samples (Raw INT16):", data[:10])
        
        # Threshold for 16-bit PCM silence
        if d_std < 10.0: 
            print("\n❌ JUDGMENT: The raw extracted audio is SILENT.")
            print("Possible causes:")
            print("1. The video file has an audio track but it contains no sound.")
            print("2. FFmpeg selected the wrong audio stream (Video might have multiple tracks).")
        else:
            print("\n✅ JUDGMENT: The raw extracted audio has SOUND.")
            print("This implies 'MoviePy' was reading it incorrectly, but FFmpeg can read it.")
            
    except Exception as e:
        print(f"Error reading wav file: {e}")
    finally:
        # Cleanup
        if os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
                print(f"\n(Removed temp file: {temp_wav})")
            except: pass

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
