
import os
import sys
import numpy as np

# setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from modules.audio_tools import AudioComparator, AudioFileClip
    from PyQt6.QtWidgets import QApplication, QFileDialog
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please run this script from the project root directory.")
    input("Press Enter to exit...")
    sys.exit(1)

def main():
    app = QApplication(sys.argv)
    
    print("--- 1. Select VIDEO File ---")
    video_path, _ = QFileDialog.getOpenFileName(None, "Select VIDEO File", "", "Video Files (*.mp4 *.avi *.mov *.mkv)")
    if not video_path:
        print("No video selected.")
        return

    print(f"Selected Video: {video_path}")
    
    print("\n--- 2. Select AUDIO File ---")
    audio_path, _ = QFileDialog.getOpenFileName(None, "Select AUDIO File", "", "Audio Files (*.mp3 *.wav *.flac)")
    if not audio_path:
        print("No audio selected.")
        return

    print(f"Selected Audio: {audio_path}")
    
    print("\n" + "="*50)
    print("STARTING ANALYSIS")
    print("="*50)

    # 1. Analyze Video Head
    print(f"\n[Reading Video Head (7s)]...")
    try:
        vid_clip = AudioFileClip(video_path)
        vid_dur = vid_clip.duration
        print(f"  -> Original Duration: {vid_dur:.4f}s")
        
        
        # Read 7s
        # Fix: compatibility check
        read_end = min(7.0, vid_dur)
        if hasattr(vid_clip, "subclipped"):
            vid_sub = vid_clip.subclipped(0, read_end)
        else:
            vid_sub = vid_clip.subclip(0, read_end)
            
        vid_arr = vid_sub.to_soundarray(fps=12000)
        vid_clip.close()
        
        # To Mono
        if len(vid_arr.shape) > 1 and vid_arr.shape[1] > 1:
            vid_arr = vid_arr.mean(axis=1)
            
        print(f"  -> Read Samples: {len(vid_arr)} (Expected ~{int(min(7.0,vid_dur)*12000)})")
        
        
        # Calculate Stats (Raw)
        raw_mean = np.mean(vid_arr)
        print(f"  -> Raw Mean: {raw_mean:.6f} (DC Offset)")
        
        # --- Fix: Center Data ---
        vid_centered = vid_arr - raw_mean
        
        # Calculate AC RMS (Std Dev)
        vid_std = np.std(vid_centered)
        print(f"  -> AC RMS (Std Dev): {vid_std:.6f}")
        print(f"  -> Min Value: {np.min(vid_arr):.6f}")
        print(f"  -> Max Value: {np.max(vid_arr):.6f}")
        
        if vid_std < 0.002:
            print("  -> WARN: Video seems SILENT (Low Variance)!")
            
        # Normalize
        vid_norm = np.linalg.norm(vid_centered)
        vid_final = vid_centered / vid_norm if vid_norm > 0 else vid_centered
        
        # Show middle samples
        mid_idx = len(vid_final) // 2
        print(f"  -> Middle 10 samples: {vid_final[mid_idx:mid_idx+10]}")
        
    except Exception as e:
        print(f"ERROR reading video: {e}")
        return

    # 2. Analyze Audio Head
    print(f"\n[Reading Audio Head (5s)]...")
    try:
        aud_clip = AudioFileClip(audio_path)
        aud_dur = aud_clip.duration
        print(f"  -> Original Duration: {aud_dur:.4f}s")
        
        # Read 5s
        read_end = min(5.0, aud_dur)
        if hasattr(aud_clip, "subclipped"):
            aud_sub = aud_clip.subclipped(0, read_end)
        else:
            aud_sub = aud_clip.subclip(0, read_end)
            
        aud_arr = aud_sub.to_soundarray(fps=12000)
        aud_clip.close()
        
        # To Mono
        if len(aud_arr.shape) > 1 and aud_arr.shape[1] > 1:
            aud_arr = aud_arr.mean(axis=1)
            
        print(f"  -> Read Samples: {len(aud_arr)} (Expected ~{int(min(5.0,aud_dur)*12000)})")
        
        
        # Calculate Stats (Raw)
        raw_mean = np.mean(aud_arr)
        print(f"  -> Raw Mean: {raw_mean:.6f} (DC Offset)")
        
        # --- Fix: Center Data ---
        aud_centered = aud_arr - raw_mean
        
        # Calculate AC RMS (Std Dev)
        aud_std = np.std(aud_centered)
        print(f"  -> AC RMS (Std Dev): {aud_std:.6f}")
        print(f"  -> Min Value: {np.min(aud_arr):.6f}")
        print(f"  -> Max Value: {np.max(aud_arr):.6f}")
        
        if aud_std < 0.002:
            print("  -> WARN: Audio seems SILENT (Low Variance)!")
            
        # Normalize
        aud_norm = np.linalg.norm(aud_centered)
        aud_final = aud_centered / aud_norm if aud_norm > 0 else aud_centered
        
        # Show middle samples
        mid_idx = len(aud_final) // 2
        print(f"  -> Middle 10 samples: {aud_final[mid_idx:mid_idx+10]}")

    except Exception as e:
        print(f"ERROR reading audio: {e}")
        return

    # 3. Perform Sliding Match
    print("\n" + "-"*30)
    print("RUNNING SLIDING MATCH")
    print("-"*30)
    
    len_v = len(vid_final)
    len_a = len(aud_final)
    
    if len_v < len_a:
        print("ERROR: Video head is shorter than Audio head. Cannot slide.")
    else:
        fps = 12000
        step = 20
        search_samples = len_v - len_a
        print(f"Scanning range: {search_samples} samples ({search_samples/fps:.3f}s)")
        
        best_score = -1.0
        best_offset = 0
        
        # Check specific offsets
        offsets_to_check = [0, int(0.1*fps), int(0.5*fps), int(1.0*fps)]
        print("\nSpot Checks:")
        
        for idx in offsets_to_check:
            if idx + len_a <= len_v:
                v_slice = vid_final[idx : idx + len_a]
                # calc dot
                v_slice_norm = np.linalg.norm(v_slice)
                if v_slice_norm > 0:
                    score = np.dot(aud_final, v_slice) / v_slice_norm
                    print(f"  Offset {idx/fps:.2f}s: Score = {score:.4f}")
                else:
                    print(f"  Offset {idx/fps:.2f}s: Video slice is SILENT")
        
        print("\nScanning all...")
        for start_idx in range(0, search_samples + 1, step):
            v_slice = vid_final[start_idx : start_idx + len_a]
            v_n = np.linalg.norm(v_slice)
            if v_n > 0.001:
                sc = np.dot(aud_final, v_slice) / v_n
                if sc > best_score:
                    best_score = sc
                    best_offset = start_idx
        
        print("\n" + "="*50)
        print(f"FINAL RESULT")
        print("="*50)
        print(f"Best Correlation Score: {best_score:.6f}")
        print(f"Best Alignment Offset : {best_offset/fps:.4f} seconds")
        
        if best_score > 0.82:
            print(">>> MATCH SUCCESS! <<<")
        else:
            print(">>> MATCH FAILED (Score too low) <<<")
            
    input("\nPress Enter to close window...")

if __name__ == "__main__":
    main()
