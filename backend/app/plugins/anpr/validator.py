import re
from typing import Tuple, Optional

class PlateValidator:
    """
    Validates and cleans license plates using regular expressions.
    Specifically targets Indian vehicle registration formats.
    """
    
    # Common OCR mistakes
    CHAR_TO_NUM = {
        'O': '0', 'Q': '0', 'D': '0',
        'I': '1', 'L': '1', 'T': '1',
        'Z': '2',
        'B': '8',
        'S': '5',
        'A': '4',
        'G': '6'
    }
    
    NUM_TO_CHAR = {
        '0': 'O',
        '1': 'I',
        '2': 'Z',
        '8': 'B',
        '5': 'S',
        '4': 'A',
        '6': 'G'
    }

    # Standard Indian Plate Format: 2 chars (state), 2 digits (RTO), 1-3 chars (series), 4 digits (number)
    # Examples: MH12AB1234, DL01CAB1234, UP16AB1234, KA05MK6789
    # We will use a flexible regex that allows optional spaces
    INDIAN_PLATE_REGEX = re.compile(r'^([A-Z]{2})\s*([0-9]{1,2})\s*([A-Z]{1,3})\s*([0-9]{4})$')

    @classmethod
    def clean_plate_string(cls, text: str) -> str:
        """Removes special characters and converts to uppercase."""
        return re.sub(r'[^A-Z0-9]', '', text.upper())

    @classmethod
    def _fix_segment(cls, segment: str, expected_type: str) -> str:
        """Fixes characters based on expected type ('char' or 'num')"""
        fixed = []
        for char in segment:
            if expected_type == 'char' and char.isdigit():
                fixed.append(cls.NUM_TO_CHAR.get(char, char))
            elif expected_type == 'num' and char.isalpha():
                fixed.append(cls.CHAR_TO_NUM.get(char, char))
            else:
                fixed.append(char)
        return "".join(fixed)

    @classmethod
    def repair_and_validate(cls, raw_plate: str) -> Tuple[bool, Optional[str]]:
        """
        Attempts to repair common OCR mistakes and validates against known formats.
        Returns (is_valid, repaired_plate).
        """
        cleaned = cls.clean_plate_string(raw_plate)
        if not cleaned:
            return False, None

        # Try exact match first
        match = cls.INDIAN_PLATE_REGEX.match(cleaned)
        if match:
            return True, cleaned

        # If not matched, try to repair based on length (typically 9-11 chars)
        if 8 <= len(cleaned) <= 11:
            # Assume structure: State(2), RTO(2), Series(1-3), Number(4)
            # We'll work backwards: last 4 must be numbers
            num_part = cleaned[-4:]
            fixed_num = cls._fix_segment(num_part, 'num')
            
            # First 2 must be chars
            state_part = cleaned[:2]
            fixed_state = cls._fix_segment(state_part, 'char')
            
            # Next 2 should be numbers (RTO)
            rto_part = cleaned[2:4]
            fixed_rto = cls._fix_segment(rto_part, 'num')
            
            # Remaining is series
            series_part = cleaned[4:-4]
            fixed_series = cls._fix_segment(series_part, 'char')
            
            candidate = f"{fixed_state}{fixed_rto}{fixed_series}{fixed_num}"
            
            # Validate candidate
            if cls.INDIAN_PLATE_REGEX.match(candidate):
                return True, candidate
                
        return False, cleaned
