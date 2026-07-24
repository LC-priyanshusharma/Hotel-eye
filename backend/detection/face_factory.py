from detection.interfaces.face import IFaceEngine
from detection.strategies.insightface import InsightFaceStrategy

class FaceFactory:
    """
    Factory to instantiate the correct Face Engine Strategy based on configuration.
    """
    
    @staticmethod
    def create(face_backend: str) -> IFaceEngine:
        name = face_backend.lower().strip()
        if name == "insightface":
            return InsightFaceStrategy()
        # Add mediapipe strategy here in the future
        else:
            raise ValueError(f"Unknown face recognition backend: {face_backend}")
