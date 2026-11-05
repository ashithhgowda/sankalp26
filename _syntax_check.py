import py_compile, sys

files = [
    "backend/server.py",
    "backend/phase1.py",
    "backend/core_utils.py",
    "backend/notification_service.py",
]

all_ok = True
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"OK   {f}")
    except py_compile.PyCompileError as e:
        print(f"FAIL {f}: {e}")
        all_ok = False

sys.exit(0 if all_ok else 1)
