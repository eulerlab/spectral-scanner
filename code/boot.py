# ----------------------------------------------------------------------------
# boot.py
# Runs at startup
#
# The MIT License (MIT)
# Copyright (c) 2020 Thomas Euler
# 2020-11-21, v1
# ----------------------------------------------------------------------------
# Disable debugging information
try:
  import esp
  esp.osdebug(None)
except ImportError:
  pass

# ----------------------------------------------------------------------------
