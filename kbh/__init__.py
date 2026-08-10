"""Copenhagen apartment monitor.

A standalone subsystem that watches the Copenhagen market for apartments in a
defined price band, scores every listing against hyperlocal benchmarks, asks
Claude for a written verdict, and pushes the good ones to Telegram.

Independent of the villa pipeline in ``src/``: own SQLite store, own config,
own web app.
"""

__version__ = "1.0.0"
