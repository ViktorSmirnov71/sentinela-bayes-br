"""Per-dam-per-month feature assembly.

Builds the table (dam_id, month) -> feature vector by joining canonical loader
outputs onto the SIGBM cohort skeleton. Output schema is contract-defined in
docs/04-methods.md §3.
"""
