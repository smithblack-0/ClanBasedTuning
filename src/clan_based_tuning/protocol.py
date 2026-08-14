"""Private Tune-result fields connecting the Lightning callback and Clan scheduler.

The callback publishes stable member identity, the independently resolved winner, and which
member supplied the round checkpoint. The scheduler validates those fields against its own
population decision before transferring the continuation, catching divergence between the
worker-side DDP view and driver-side Tune view.
"""

CLAN_MEMBER_ID = "clan/member_id"
CLAN_WINNER_ID = "clan/winner_id"
CLAN_CHECKPOINT_SOURCE = "clan/checkpoint_source"
