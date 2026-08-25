FROM nvcr.io/nvidia/deepstream:7.1-samples-multiarch

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    python3-opencv \
    libglib2.0-dev \
    libgirepository1.0-dev \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-gst-plugins-base-1.0 \
    gir1.2-gstreamer-1.0 \
    git \
    build-essential \
    cmake \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pyds wheel (DeepStream 7.1 Python bindings for Python 3.10 on aarch64)
RUN pip3 install --no-cache-dir \
    https://github.com/NVIDIA-AI-IOT/deepstream_python_apps/releases/download/v1.1.11/pyds-1.1.11-py3-none-linux_aarch64.whl \
    redis numpy loguru

# Clone and compile DeepStream-Yolo custom bbox parser with CUDA 12.6 / TensorRT 10
WORKDIR /app/deepstream
RUN git clone https://github.com/marcoslucianops/DeepStream-Yolo.git /app/deepstream/DeepStream-Yolo && \
    cd /app/deepstream/DeepStream-Yolo/nvdsinfer_custom_impl_Yolo && \
    CUDA_VER=12.6 make

COPY . /app/deepstream
WORKDIR /app/deepstream

CMD ["python3", "pipeline.py"]
