import os
import shutil
import tempfile
from pathlib import Path

_test_data_dir = Path(tempfile.mkdtemp(prefix="atlas-test-"))
os.environ["XDG_DATA_HOME"] = str(_test_data_dir)

from atlas import index
from atlas.errors import IndexCorrupt

results = []  # (label, passed, detail)


def check(label, condition):
    results.append((label, bool(condition), ""))


def reset():
    """Wipe the test data dir between test groups so each one starts clean."""
    shutil.rmtree(_test_data_dir, ignore_errors=True)
    _test_data_dir.mkdir(parents=True, exist_ok=True)


def test_missing_file():
    reset()
    idx = index.load()
    check("load() on missing file: version=1", idx.version == 1)
    check("load() on missing file: no projects", idx.projects == [])


def test_round_trip():
    reset()
    idx = index.load()
    index.insert(idx, index.IndexEntry(name="keylo", path="/home/aj/projects/keylo"))
    index.save(idx)

    idx2 = index.load()
    check("round trip: one project", len(idx2.projects) == 1)
    check("round trip: name matches", idx2.projects[0].name == "keylo")
    check("round trip: path matches", idx2.projects[0].path == "/home/aj/projects/keylo")
    check("round trip: last_opened still None", idx2.projects[0].last_opened is None)


def test_find_by_name():
    reset()
    idx = index.load()
    index.insert(idx, index.IndexEntry(name="keylo", path="/x"))
    index.save(idx)
    idx = index.load()

    found = index.find_by_name(idx, "keylo")
    check("find_by_name: finds existing entry", found is not None and found.name == "keylo")

    missing = index.find_by_name(idx, "nonexistent")
    check("find_by_name: None for missing entry", missing is None)


def test_update_last_opened():
    reset()
    idx = index.load()
    index.insert(idx, index.IndexEntry(name="keylo", path="/x"))
    index.save(idx)
    idx = index.load()

    index.update_last_opened(idx, "keylo")
    check("update_last_opened: sets timestamp in memory", idx.projects[0].last_opened is not None)

    index.save(idx)
    idx2 = index.load()
    check("update_last_opened: persists after reload", idx2.projects[0].last_opened is not None)


def test_insert_and_remove():
    reset()
    idx = index.load()
    index.insert(idx, index.IndexEntry(name="keylo", path="/x"))
    index.insert(idx, index.IndexEntry(name="zenith", path="/y"))
    index.save(idx)

    idx2 = index.load()
    check("insert: two projects present", len(idx2.projects) == 2)

    index.remove(idx2, "keylo")
    index.save(idx2)

    idx3 = index.load()
    check("remove: one project left", len(idx3.projects) == 1)
    check("remove: correct project remains", idx3.projects[0].name == "zenith")

    index.remove(idx3, "does-not-exist")
    check("remove: removing an unknown name is a no-op, doesn't raise", len(idx3.projects) == 1)


def test_corrupted_file():
    reset()
    bad_path = index._index_path()
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text("{ not valid json")

    raised = False
    try:
        index.load()
    except IndexCorrupt:
        raised = True
    check("load() raises IndexCorrupt on bad JSON", raised)


def test_atomic_write():
    """
    Simulates a crash between the write and the rename by making
    Path.replace explode partway through save(). Confirms the real
    index.json is untouched when that happens — this is the whole
    point of the tmp + replace pattern.
    """
    reset()
    idx = index.load()
    index.insert(idx, index.IndexEntry(name="original", path="/x"))
    index.save(idx)

    before = index._index_path().read_text()

    idx.projects[0].name = "should-never-land-on-disk"

    def _exploding_replace(self, target):
        raise OSError("simulated crash mid-save")

    original_replace = Path.replace
    Path.replace = _exploding_replace

    crashed = False
    try:
        index.save(idx)
    except OSError:
        crashed = True
    finally:
        Path.replace = original_replace

    check("atomic write: save() propagates the simulated crash", crashed)

    after = index._index_path().read_text()
    check("atomic write: real index.json untouched by the failed save", before == after)


def main():
    tests = [
        test_missing_file,
        test_round_trip,
        test_find_by_name,
        test_update_last_opened,
        test_insert_and_remove,
        test_corrupted_file,
        test_atomic_write,
    ]

    for t in tests:
        print(f"\n── {t.__name__} " + "─" * max(0, 50 - len(t.__name__)))
        start = len(results)
        try:
            t()
        except Exception as e:
            results.append((f"{t.__name__} crashed", False, f"{type(e).__name__}: {e}"))
        for label, ok, detail in results[start:]:
            mark = "✓" if ok else "✗"
            extra = f" — {detail}" if detail else ""
            print(f"  {mark} {label}{extra}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{passed} passed, {failed} failed")

    shutil.rmtree(_test_data_dir, ignore_errors=True)

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()