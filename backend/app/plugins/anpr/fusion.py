from typing import List, Dict, Optional, Tuple
from collections import defaultdict

class OcrObservation:
    def __init__(self, text: str, confidence: float, timestamp: float):
        self.text = text
        self.confidence = confidence
        self.timestamp = timestamp

class TemporalFusion:
    """
    Accumulates OCR observations for a tracked vehicle and fuses them
    to determine the most probable license plate using weighted majority voting.
    """
    def __init__(self):
        self.observations: List[OcrObservation] = []

    def add_observation(self, text: str, confidence: float, timestamp: float):
        self.observations.append(OcrObservation(text, confidence, timestamp))

    def get_best_plate(self) -> Tuple[Optional[str], float]:
        from app.plugins.anpr.config_parser import anpr_app_config
        
        if len(self.observations) < anpr_app_config.fusion.min_observations:
            return None, 0.0

        # Weighted majority voting
        plate_scores: Dict[str, float] = defaultdict(float)
        
        for obs in self.observations:
            # We weight by confidence.
            # Could also decay older observations, but tracking spans are short (few seconds)
            plate_scores[obs.text] += obs.confidence
            
        if not plate_scores:
            return None, 0.0

        # Find plate with max aggregated score
        best_plate = max(plate_scores.items(), key=lambda x: x[1])
        
        # Calculate a normalized confidence for the winning plate
        # Average confidence of observations that voted for this plate
        winning_plate = best_plate[0]
        winning_votes = [obs.confidence for obs in self.observations if obs.text == winning_plate]
        avg_confidence = sum(winning_votes) / len(winning_votes) if winning_votes else 0.0
        
        return winning_plate, avg_confidence
