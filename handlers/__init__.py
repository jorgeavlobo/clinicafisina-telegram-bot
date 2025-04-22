from importlib import import_module
from pathlib import Path

# Dynamically import all routers for auto‑registration
all_routers = []

for path in Path(__file__).parent.rglob("*_router.py"):
    module_path = ".".join(path.relative_to(Path(__file__).parent).with_suffix("").parts)
    mod = import_module(f"handlers.{module_path}")
    router = getattr(mod, "router", None)
    if router:
        all_routers.append(router)
