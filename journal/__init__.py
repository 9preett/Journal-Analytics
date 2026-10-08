"""Journal Analytics - a desktop app that stores journal metadata and analyses writing habits.

Modules
-------
validators   : input validation helpers (raise ``ValidationError``)
models       : the ``Entry`` data structure and factory function
storage      : persistent JSON storage + CSV import/export
analytics    : Pandas/NumPy based analysis (counts, frequency, streaks, patterns)
visuals      : Matplotlib chart builders
sample_data  : reproducible demo-data generator
gui          : Tkinter user interface
"""

__version__ = "1.0.0"
