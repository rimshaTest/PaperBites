import time
from paper.latest import _translate_to_english

start = time.monotonic()
result = _translate_to_english("Andamios y viaductos en la sima de la Fenomenologia", "es")
print("Result:", result)
print("Took:", time.monotonic() - start, "seconds")
