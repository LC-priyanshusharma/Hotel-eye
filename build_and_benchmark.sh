#!/bin/bash
# Script to convert ONNX to TensorRT engine and benchmark on Jetson (JetPack 6.2 / DeepStream 7.1 / TRT 10)
# Run this from the root of the LogicEye-main directory on the Jetson terminal

set -e

echo "========================================="
echo "1. Building TensorRT Engine (FP16)..."
echo "========================================="
# Using DeepStream 7.1 container with TensorRT 10 to access trtexec
sudo docker run --rm --runtime=nvidia -v $(pwd):/app nvcr.io/nvidia/deepstream:7.1-samples-multiarch \
    /usr/src/tensorrt/bin/trtexec \
    --onnx=/app/backend/detection/yolo11n_opset12.onnx \
    --saveEngine=/app/backend/detection/yolo11n_opset12.onnx_b30_gpu0_fp16.engine \
    --fp16 \
    --memPoolSize=workspace:4096

# Also create symlink or copy for convenience
cp -f backend/detection/yolo11n_opset12.onnx_b30_gpu0_fp16.engine backend/detection/yolo11n.engine 2>/dev/null || true

echo ""
echo "========================================="
echo "2. Benchmarking TensorRT Engine..."
echo "========================================="
sudo docker run --rm --runtime=nvidia -v $(pwd):/app nvcr.io/nvidia/deepstream:7.1-samples-multiarch \
    /usr/src/tensorrt/bin/trtexec \
    --loadEngine=/app/backend/detection/yolo11n_opset12.onnx_b30_gpu0_fp16.engine \
    --fp16 \
    --iterations=200 \
    --avgRuns=10 \
    --duration=10

echo "Done! Review the latency and FPS (qps) metrics above."
