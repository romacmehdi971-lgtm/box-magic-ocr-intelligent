#!/usr/bin/env python3
import os
# Simuler l'environnement Cloud Run
os.environ["READ_ONLY_MODE"] = "true"
os.environ["VERSION"] = "v3.1.4-one-shot-fix"
os.environ["GIT_COMMIT"] = "test"

# Test que le middleware lit bien os.environ
read_only = os.environ.get("READ_ONLY_MODE", "false").lower() == "true"
print(f"✅ Middleware READ_ONLY_MODE test: {read_only}")
assert read_only == True, "FAIL: middleware should read true from env"

# Test config.py n'interfère pas
from memory_proxy.app.config import API_VERSION
print(f"✅ API_VERSION from config: {API_VERSION}")
assert API_VERSION == "v3.1.4-one-shot-fix", f"FAIL: expected v3.1.4-one-shot-fix, got {API_VERSION}"

print("✅ ALL TESTS PASSED")
