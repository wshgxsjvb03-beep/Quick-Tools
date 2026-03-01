import os
import inspect

try:
    from playwright._impl._driver import compute_driver_executable, get_driver_env
    print("compute_driver_executable:", compute_driver_executable())
except Exception as e:
    print("Error:", e)
