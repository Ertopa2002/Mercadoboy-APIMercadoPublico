from mp_core.store import MemoryStore


def test_memory_store_expira():
    t = [1000.0]
    s = MemoryStore(reloj=lambda: t[0])
    s.put("a", {"x": 1}, ttl_s=10)
    assert s.get("a") == {"x": 1}
    t[0] += 11
    assert s.get("a") is None


def test_memory_store_incr():
    s = MemoryStore()
    assert s.incr("c") == 1
    assert s.incr("c", 5) == 6
    s.delete("c")
    assert s.get("c") is None
