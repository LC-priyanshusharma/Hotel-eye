import pytest
import uuid

def generate_visitor_id() -> str:
    # Generates a permanent immutable Visitor ID: e.g. VIS-84F12C91
    return f"VIS-{uuid.uuid4().hex[:8].upper()}"

def generate_visit_id() -> str:
    return f"VT-{uuid.uuid4().hex[:8].upper()}"

class TestVisitorRepositoryUtils:
    def test_generate_visitor_id_format(self):
        v_id = generate_visitor_id()
        assert v_id.startswith("VIS-")
        assert len(v_id) == 12 # 4 + 8
        assert v_id[4:].isalnum()
        assert v_id[4:].isupper()

    def test_generate_visit_id_format(self):
        vt_id = generate_visit_id()
        assert vt_id.startswith("VT-")
        assert len(vt_id) == 11 # 3 + 8
        assert vt_id[3:].isalnum()
        assert vt_id[3:].isupper()

    def test_unique_generation(self):
        ids = set(generate_visitor_id() for _ in range(1000))
        assert len(ids) == 1000
