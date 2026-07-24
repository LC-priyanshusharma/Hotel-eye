import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# Assuming these will be implemented
try:
    from detection.strategies.openvino import OpenVINOStrategy
    from detection.strategies.coreml import CoreMLStrategy
    from detection.strategies.onnx import ONNXStrategy
    from detection.strategies.tensorrt import TensorRTStrategy
except ImportError:
    pass

@pytest.fixture
def mock_yolo():
    # Patch YOLO at the module level where it's used
    with patch("detection.strategies.openvino.YOLO") as mock_ov, \
         patch("detection.strategies.coreml.YOLO") as mock_cml, \
         patch("detection.strategies.onnx.YOLO") as mock_onnx, \
         patch("detection.strategies.tensorrt.YOLO") as mock_trt:
        
        instance = MagicMock()
        instance.return_value = [{"mock": "detect"}]
        instance.track.return_value = [{"mock": "track"}]
        
        mock_ov.return_value = instance
        mock_cml.return_value = instance
        mock_onnx.return_value = instance
        mock_trt.return_value = instance
        
        yield instance

@pytest.mark.parametrize("StrategyClass, expected_format", [
    ("OpenVINOStrategy", "openvino"),
    ("CoreMLStrategy", "coreml"),
    ("ONNXStrategy", "onnx"),
    ("TensorRTStrategy", "engine"),
])
def test_strategy_exports_and_loads(mock_yolo, StrategyClass, expected_format):
    try:
        Strategy = globals()[StrategyClass]
    except KeyError:
        pytest.skip(f"{StrategyClass} not implemented yet.")
        
    # Mock os.path.exists to simulate model not being exported yet
    with patch("os.path.exists", return_value=False):
        strategy = Strategy(model_path="dummy.pt", conf=0.5, classes=[0])
        
        # Verify export was called with correct format
        mock_yolo.export.assert_called_once_with(format=expected_format, half=False)
        
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    
    # Test detect
    res = strategy.detect(frame)
    assert res == {"mock": "detect"}

