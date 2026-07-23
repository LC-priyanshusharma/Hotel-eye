import pytest
from app.plugins.anpr.fusion import TemporalFusion

def test_temporal_fusion():
    fusion = TemporalFusion()
    
    # Simulating frames
    fusion.add_observation("MH12AB1234", 0.82, 100.0)
    fusion.add_observation("MH12AB1234", 0.94, 100.1)
    fusion.add_observation("MH12AB1234", 0.98, 100.2)
    # One mistake
    fusion.add_observation("MH12AB1Z34", 0.60, 100.3)
    
    best_plate, confidence = fusion.get_best_plate()
    
    assert best_plate == "MH12AB1234"
    # Average of 0.82, 0.94, 0.98 is 0.9133...
    assert pytest.approx(confidence, 0.01) == 0.913

def test_empty_fusion():
    fusion = TemporalFusion()
    best_plate, confidence = fusion.get_best_plate()
    assert best_plate is None
    assert confidence == 0.0
