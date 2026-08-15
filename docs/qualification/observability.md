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
- selected checkpoint-source member and fitness;
- runtime timeout boundaries before the corresponding exception is raised; and
- successful experiment runtime release after the complete population finishes.

Generation logs include only mutation-controlled keys when showing parent/child values. They
do not dump an arbitrary full user Tune config.

A pre-DDP rendezvous timeout retracts the timed-out member's exact pending announcement before
the timeout is logged/raised, so later diagnostics are not polluted by a session formed with a
dead peer.

Applications configure logging using ordinary Python mechanisms. No CBT-specific logging
configuration is required. These messages are diagnostic evidence, not a durable machine API;
programs should use the public Tune/Lightning results rather than parsing log text.
