# Third-party notices

## Ray Tune

`src/clan_based_tuning/ray_compat.py` and the synchronous scheduler transition were designed
from direct study of Ray Tune's Population Based Training implementation and preserve the
same underlying Tune checkpoint/pause/config-transfer behavior where Tune has no stable
single-operation public equivalent.

Ray is copyright The Ray Authors and is distributed under the Apache License 2.0. The
ClanBasedTuning implementation intentionally rewrites and reduces that behavior to the
Clan-specific subset rather than vendoring Ray's full PBT source. This notice records the
implementation provenance; it does not select a license for ClanBasedTuning as a whole.
