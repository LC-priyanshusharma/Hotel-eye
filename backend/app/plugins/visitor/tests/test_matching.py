import pytest
import numpy as np

def cosine_similarity(vec1: list, vec2: list) -> float:
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

class TestVisitorMatching:
    def test_cosine_similarity_identical(self):
        vec1 = [0.1] * 512
        vec2 = [0.1] * 512
        sim = cosine_similarity(vec1, vec2)
        assert sim > 0.99

    def test_cosine_similarity_different(self):
        vec1 = [0.1] * 512
        vec2 = [-0.1] * 512
        sim = cosine_similarity(vec1, vec2)
        assert sim < -0.99

    def test_cosine_similarity_orthogonal(self):
        vec1 = [1.0] + [0.0] * 511
        vec2 = [0.0, 1.0] + [0.0] * 510
        sim = cosine_similarity(vec1, vec2)
        assert abs(sim) < 0.01

    def test_matching_threshold(self):
        threshold = 0.6
        # Simulate an embedding from the DB
        db_embedding = np.random.randn(512).tolist()
        
        # Simulate an identical embedding
        live_embedding = db_embedding
        assert cosine_similarity(db_embedding, live_embedding) >= threshold

        # Simulate a completely different embedding
        other_embedding = np.random.randn(512).tolist()
        assert cosine_similarity(db_embedding, other_embedding) < threshold
