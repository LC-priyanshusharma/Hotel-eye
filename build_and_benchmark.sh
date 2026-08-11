#!/bin/bash
# Script to convert ONNX to TensorRT engine and benchmark on Jetson Nano
# Run this from the root of the LogicEye-main directory on the Jetson terminal

echo "========================================="
echo "1. Building TensorRT Engine (FP16)..."
echo "========================================="
# Using the verified l4t-pytorch container to access trtexec
sudo docker run --rm --runtime=nvidia -v $(pwd):/app nvcr.io/nvidia/l4t-pytorch:r32.7.1-pth1.10-py3 \
    /usr/src/tensorrt/bin/trtexec \
    --onnx=/app/backend/detection/yolo11n_opset12.onnx \
    --saveEngine=/app/backend/detection/yolo11n.engine \
    --fp16 \
    --workspace=1024

echo ""
echo "========================================="
echo "2. Benchmarking TensorRT Engine..."
echo "========================================="
sudo docker run --rm --runtime=nvidia -v $(pwd):/app nvcr.io/nvidia/l4t-pytorch:r32.7.1-pth1.10-py3 \
    /usr/src/tensorrt/bin/trtexec \
    --loadEngine=/app/backend/detection/yolo11n.engine \
    --fp16 \
    --iterations=200 \
    --avgRuns=10 \
    --duration=10

echo "Done! Review the latency and FPS (qps) metrics above."
