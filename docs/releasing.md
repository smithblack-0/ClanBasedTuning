# Release policy

ClanBasedTuning is pre-1.0. Releases may change APIs between minor versions when the change is
necessary, but release notes must state such changes explicitly. Patch releases should be
reserved for compatible fixes within an already documented pre-release surface.

A release claim may never be broader than its direct qualification evidence. Dependency
metadata may intentionally admit multiple compatible framework minors without claiming every
admitted combination has been tested.

## Release candidate checklist

1. Install the development environment from a clean checkout.
2. Run Ruff lint and format checks.
3. Run the maintained package-source mypy contract.
4. Run the complete ordinary pytest suite, including real Ray/Lightning CPU contracts.
5. Run every opt-in hardware/topology/failure contract needed for support claims in this
   release and record the concrete environment.
6. Run representative performance measurements for any performance claim being published.
7. Build fresh wheel and sdist artifacts.
8. Run `python -m twine check dist/*` on those exact artifacts.
9. Install the wheel non-editably in a clean environment and verify the public package surface.
10. Synchronize README, API docs, examples, STATUS, qualification records, security policy,
    and CHANGELOG with the exact evidence.
11. Confirm dependency bounds remain compatibility bounds rather than convenience point pins.
12. Complete the mandatory final style/quality re-audit and fix every concrete issue it finds.
13. Confirm a project license has been selected by the owner and included in release metadata.

No release is approved merely because CI is green.

## Legal/license gate

The repository does not choose a license on behalf of the project owner. Until the owner
selects license terms, an ordinary open-source/public production release remains blocked.
Once selected, add the license file and corresponding package metadata as one explicit owner-
approved change.

## Publishing

This repository currently treats artifact construction and validation as the automated
boundary. A maintainer publishes only after the checklist above is complete. Do not add
registry credentials or autonomous publishing authority merely to make release automation
more convenient.
