import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# langdetect is only needed by paper/latest.py's language detection and doesn't build on every
# platform; stub it so the pipeline tests can import that module without it.
try:
    import langdetect  # noqa: F401
except Exception:
    stub = types.ModuleType("langdetect")

    class DetectorFactory:
        seed = 0

    class LangDetectException(Exception):
        pass

    stub.DetectorFactory = DetectorFactory
    stub.LangDetectException = LangDetectException
    stub.detect_langs = lambda text: []
    sys.modules["langdetect"] = stub
