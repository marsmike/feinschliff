# Per-subcommand modules for `feinschliff deck …`.
#
# Each module exports `register(sub)` which adds its own argparse parsers
# (with `func=` defaults) to the deck subparser group. `cli/deck.py` calls
# these in turn to keep its own size manageable.
