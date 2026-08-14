# Operational diagnostics

Status: standard logging at Clan-owned lifecycle boundaries.

ClanBasedTuning uses Python's standard `logging` infrastructure rather than introducing a
second telemetry runtime. Ray, Lightning, and PyTorch retain their own execution/backend
logging.

CBT emits diagnostics for:

- complete cohort registration with experiment and stable trial/member population;
- member rendezvous/join with stable member ID and world size;
- each reported generation boundary and current report count;
- resolved generation, winner ID, selected parent mutation values, and child mutation values;
- selected checkpoint-source member and fitness; and
- runtime timeout boundaries before the corresponding exception is raised.

Generation logs include only mutation-controlled keys when showing parent/child values. They
do not dump an arbitrary full user Tune config.

Applications configure logging using ordinary Python mechanisms. No CBT-specific logging
configuration is required. These messages are diagnostic evidence, not a durable machine API;
programs should use the public Tune/Lightning results rather than parsing log text.
