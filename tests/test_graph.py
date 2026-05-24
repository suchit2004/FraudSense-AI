import time
from backend.graph_engine import GraphEngine

def test_graph_cycle_detection():
    engine = GraphEngine(max_edges=100)
    now = time.time()
    
    # Linear path (no cycles)
    engine.add_transaction("A@ybl", "B@ybl", 100.0, now)
    engine.add_transaction("B@ybl", "C@ybl", 100.0, now)
    assert len(engine.detect_cycles()) == 0
    assert engine.is_in_cycle("A@ybl") is False
    
    # Close the cycle: C -> A
    engine.add_transaction("C@ybl", "A@ybl", 100.0, now)
    
    cycles = engine.detect_cycles()
    assert len(cycles) > 0
    # The cycle should contain A, B, C
    cycle_nodes = cycles[0]
    assert "A@ybl" in cycle_nodes
    assert "B@ybl" in cycle_nodes
    assert "C@ybl" in cycle_nodes
    assert engine.is_in_cycle("A@ybl") is True

def test_graph_mule_detection():
    engine = GraphEngine(max_edges=100)
    now = time.time()
    
    # Suspect mule node: receives money from 3 distinct sources, forwards nothing (a pure sink)
    engine.add_transaction("source_1@ybl", "mule_sink@ybl", 1000.0, now)
    engine.add_transaction("source_2@ybl", "mule_sink@ybl", 2000.0, now)
    engine.add_transaction("source_3@ybl", "mule_sink@ybl", 1500.0, now)
    
    mules = engine.detect_mule_nodes(top_n=5)
    assert len(mules) > 0
    assert mules[0]['vpa'] == "mule_sink@ybl"
    assert "Sink Account" in mules[0]['reason']

if __name__ == "__main__":
    test_graph_cycle_detection()
    test_graph_mule_detection()
    print("✅ All Graph engine tests passed!")
