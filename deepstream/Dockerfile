FROM nvcr.io/nvidia/deepstream-l4t:6.0.1-samples

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    python3-opencv \
    libglib2.0-dev \
    python-gi-dev \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-gst-plugins-base-1.0 \
    gir1.2-gstreamer-1.0 \
    && rm -rf /var/lib/apt/lists/*

# Install pyds wheel (DeepStream Python bindings) for DS 6.0
RUN wget https://github.com/NVIDIA-AI-IOT/deepstream_python_apps/releases/download/v1.1.1/pyds-1.1.1-py3-none-linux_aarch64.whl && \
    pip3 install --no-cache-dir pyds-1.1.1-py3-none-linux_aarch64.whl redis numpy loguru && \
    rm pyds-1.1.1-py3-none-linux_aarch64.whl

COPY . /app/deepstream
WORKDIR /app/deepstream

CMD ["python3", "pipeline.py"]
