import pytest
from app.plugins.anpr.validator import PlateValidator

def test_valid_plate():
    is_valid, plate = PlateValidator.repair_and_validate("MH12AB1234")
    assert is_valid
    assert plate == "MH12AB1234"

def test_plate_with_spaces_and_special_chars():
    is_valid, plate = PlateValidator.repair_and_validate("MH-12 AB 1234")
    assert is_valid
    assert plate == "MH12AB1234"

def test_ocr_mistake_repair():
    # O instead of 0, I instead of 1, S instead of 5
    is_valid, plate = PlateValidator.repair_and_validate("MH1ZABI2S4")
    assert is_valid
    assert plate == "MH12AB1254"
    
def test_ocr_mistake_state_code():
    # 0 instead of O for state code (e.g., OR)
    is_valid, plate = PlateValidator.repair_and_validate("0R02AB1234")
    assert is_valid
    assert plate == "OR02AB1234"

def test_invalid_plate():
    # Too short
    is_valid, plate = PlateValidator.repair_and_validate("MH12")
    assert not is_valid

    # Completely wrong format
    is_valid, plate = PlateValidator.repair_and_validate("HELLO1234567")
    assert not is_valid

def test_3_char_series():
    is_valid, plate = PlateValidator.repair_and_validate("DL01CAB1234")
    assert is_valid
    assert plate == "DL01CAB1234"
