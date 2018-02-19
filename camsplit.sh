#!/bin/bash

# start copying video from real webcam to loopbacks
ffmpeg -f video4linux2 -framerate 15 -video_size 960x720 -input_format yuyv422 -i /dev/video2 -vcodec copy -f v4l2 /dev/video0 -vcodec copy -f v4l2 /dev/video1
