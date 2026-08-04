import re
from typing import Tuple, Optional, List
from app.plugins.anpr.config_parser import anpr_app_config

class PlateValidator:
    """
    Validates and cleans license plates based on configurable strategies.
    Supports smart repair for common OCR mistakes.
    """
    
    CHAR_TO_NUM = {
        'O': '0', 'Q': '0', 'D': '0',
        'I': '1', 'L': '1', 'T': '1',
        'Z': '2', 'B': '8', 'S': '5',
        'A': '4', 'G': '6'
    }
    
    NUM_TO_CHAR = {
        '0': 'O', '1': 'I', '2': 'Z',
        '8': 'B', '5': 'S', '4': 'A', '6': 'G'
    }

    # Format strategies (simplified for regex representation)
    STRATEGIES = {
        "private": re.compile(r'^([A-Z]{2})\s*([0-9]{1,2})\s*([A-Z]{0,3})\s*([0-9]{4})$'),
        "commercial": re.compile(r'^([A-Z]{2})\s*([0-9]{1,2})\s*([A-Z]{0,3})\s*([0-9]{4})$'),
        "ev": re.compile(r'^([A-Z]{2})\s*([0-9]{1,2})\s*([A-Z]{0,3})\s*([0-9]{4})$'),
        "diplomatic": re.compile(r'^([0-9]{1,3})\s*(CD|CC)\s*([0-9]{1,4})$'),
        "military": re.compile(r'^\u2191\s*([0-9]{2})\s*([A-Z])\s*([0-9]{4,6})\s*([A-Z])$'),
        "bh_series": re.compile(r'^([0-9]{2})\s*BH\s*([0-9]{4})\s*([A-Z]{1,2})$')
    }

    @classmethod
    def clean_plate_string(cls, text: str) -> str:
        # For military, keep up arrow if present, otherwise strip non-alphanumeric
        return re.sub(r'[^\w\u2191]', '', text.upper())

    @classmethod
    def _fix_segment(cls, segment: str, expected_type: str) -> str:
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
    def repair_and_validate(cls, raw_plate: str, confidence: float = 1.0) -> Tuple[bool, Optional[str]]:
        cleaned = cls.clean_plate_string(raw_plate)
        if not cleaned:
            return False, None

        active_strategies = anpr_app_config.validation.format_strategies
        
        # 1. Try exact match against active strategies
        for strategy in active_strategies:
            regex = cls.STRATEGIES.get(strategy)
            if regex and regex.match(cleaned):
                return True, cleaned

        # 2. Smart Repair (always run if enabled to strictly enforce 'O' vs '0' on Indian formats)
        if anpr_app_config.validation.smart_repair_enabled:
            # We attempt repair assuming standard format (State, RTO, Series, Number)
            if 6 <= len(cleaned) <= 11 and ("private" in active_strategies or "commercial" in active_strategies):
                state_part = cls._fix_segment(cleaned[:2], 'char')
                num_part = cls._fix_segment(cleaned[-4:], 'num')
                middle_part = cleaned[2:-4]
                
                # Try RTO length 1 or 2
                for rto_len in [1, 2]:
                    if rto_len > len(middle_part):
                        continue
                        
                    rto_part = cls._fix_segment(middle_part[:rto_len], 'num')
                    series_part = cls._fix_segment(middle_part[rto_len:], 'char')
                    
                    candidate = f"{state_part}{rto_part}{series_part}{num_part}"
                    
                    # Check candidate against standard format
                    if cls.STRATEGIES["private"].match(candidate):
                        return True, candidate

        # Strict validation: If it doesn't match an Indian plate format, REJECT it.
        # This completely eliminates hallucinations like "PE3G4" or partial reads.
        return False, cleaned
