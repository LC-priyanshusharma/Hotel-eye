#!/usr/bin/env python3
import argparse
import subprocess
import time
import os

def main():
    parser = argparse.ArgumentParser(description="LogicEye 50-Camera RTSP Load Simulator")
    parser.add_argument("--cameras", type=int, default=5, help="Number of simulated cameras to spawn")
    parser.add_argument("--video", type=str, default="CHECK IN.mp4", help="Source video file to loop")
    parser.add_argument("--mediamtx-url", type=str, default="rtsp://localhost:8554", help="MediaMTX Base URL")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print(f"Error: Video file {args.video} not found.")
        return

    print(f"Starting {args.cameras} simulated RTSP streams to {args.mediamtx_url}...")
    
    processes = []
    
    for i in range(args.cameras):
        cam_id = f"camera_{str(i+1).zfill(3)}"
        rtsp_target = f"{args.mediamtx_url}/{cam_id}"
        
        # FFmpeg command to read a local file and push it to MediaMTX via RTSP
        # -re : Read input at native frame rate (prevents fast-forwarding bug)
        # -stream_loop -1 : Loop infinitely
        # -c copy : Avoid re-encoding to save CPU on the load tester
        cmd = [
            "ffmpeg",
            "-re", 
            "-stream_loop", "-1",
            "-i", args.video,
            "-c", "copy",
            "-f", "rtsp",
            "-rtsp_transport", "tcp",
            rtsp_target
        ]
        
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(p)
        print(f"Started {cam_id} -> {rtsp_target}")
        
    print(f"\nAll {args.cameras} cameras are now streaming.")
    print("Press Ctrl+C to stop the simulator.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all cameras...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        print("Simulator shutdown complete.")

if __name__ == "__main__":
    main()
