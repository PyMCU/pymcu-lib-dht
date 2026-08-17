# Private implementation of the dht library: core, decode, avr.
#
# A package rather than a set of _dht_*.py modules because the compiler's
# include path is flat and shared with every other installed library -- a bare
# core.py would be a global name. Everything the user is meant to import lives
# one level up, in dht.py and adafruit_dht.py.
