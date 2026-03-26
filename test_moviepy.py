import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QPixmap
import numpy as np
import os

app = QApplication(sys.argv)

def test_thumbnail(path):
    print("Testing:", path)
    if not os.path.exists(path):
        print("File does not exist")
        return
    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(path)
        t = min(1.0, clip.duration / 2.0) if hasattr(clip, 'duration') and clip.duration else 0.0
        print("Extracting frame at t =", t)
        frame = clip.get_frame(t)
        clip.close()
        
        print("Frame shape:", frame.shape)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        
        # Ensure contiguous
        frame_copy = np.ascontiguousarray(frame)
        qimg = QImage(frame_copy.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        print("QImage isNull:", qimg.isNull())
        
        pixmap = QPixmap.fromImage(qimg)
        print("QPixmap isNull:", pixmap.isNull())
    except Exception as e:
        print("Error:", e)

# Create a small dummy video first
from moviepy.editor import ColorClip
print("Creating dummy clip...")
dummy = ColorClip(size=(640, 480), color=(255, 0, 0), duration=2)
dummy.write_videofile("dummy.mp4", fps=24, logger=None)
test_thumbnail("dummy.mp4")
