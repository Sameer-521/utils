#!/usr/bin/env python3
import sys
import os

_ME = os.path.dirname(os.path.abspath(__file__))
if _ME not in sys.path:
    sys.path.insert(0, _ME)

from cli import main

sys.exit(main())
