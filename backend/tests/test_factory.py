import pytest
from unittest.mock import patch, MagicMock

# Assuming these will be implemented
from detection.factory import InferenceFactory
from detection.strategies.openvino import OpenVINOStrategy
from detection.strategies.coreml import CoreMLStrategy
from detection.strategies.onnx import ONNXStrategy
from detection.strategies.tensorrt import TensorRTStrategy

@patch("detection.strategies.openvino.YOLO")
@patch("detection.strategies.coreml.YOLO")
@patch("detection.strategies.onnx.YOLO")
@patch("detection.strategies.tensorrt.YOLO")
@patch("os.path.exists", return_value=True)
def test_inference_factory_valid_backends(mock_exists, mock_trt, mock_onnx, mock_cml, mock_ov):
    factory = InferenceFactory()
    
    # Test valid creations
    ov_engine = factory.create("openvino", "dummy.pt", 0.5, [0])
    assert isinstance(ov_engine, OpenVINOStrategy)
    
    cml_engine = factory.create("coreml", "dummy.pt", 0.5, [0])
    assert isinstance(cml_engine, CoreMLStrategy)
    
    onnx_engine = factory.create("onnx", "dummy.pt", 0.5, [0])
    assert isinstance(onnx_engine, ONNXStrategy)
    
    trt_engine = factory.create("tensorrt", "dummy.pt", 0.5, [0])
    assert isinstance(trt_engine, TensorRTStrategy)

def test_inference_factory_invalid_backend():
    factory = InferenceFactory()
    
    with pytest.raises(ValueError, match="Unsupported inference backend"):
        factory.create("invalid_backend", "dummy.pt", 0.5, [0])
