# Nick and automatic dual wielding

## What the static data shows

`Target_MainHandAttack` owns both parts of BG3's automatic dual-wield sequence:

- The normal cost is `ActionPoint:1`.
- The optional automatic off-hand cost is `DualWieldingUseCosts "BonusActionPoint:1"`.
- The off-hand roll and damage are nested in `CastOffhand[...]` sections of the same spell.

The current Nick implementation grants `WM55_NICK_READY` after a qualifying main-hand attack. That status makes `Target_OffhandAttack` free. It is removed only by an off-hand attack whose spell ID is exactly `Target_OffhandAttack`.

The likely failure is therefore:

1. `Target_MainHandAttack` grants `WM55_NICK_READY`.
2. Its nested `CastOffhand[...]` attack runs.
3. That nested attack is not the separate `Target_OffhandAttack` spell, so it does not consume `WM55_NICK_READY`.
4. The separate off-hand button remains free.

## Run the diagnostic

This instrumentation observes events only. It does not replace spells, change costs, apply statuses, or affect a character without `WM55_Known_Nick`.

1. Install the development build with Script Extender v29 or newer.
2. Open the Script Extender console and keep it in the default `server` context.
3. Enter `!wm55_nick_debug on`.
4. Start a clean combat turn with a Nick character, two qualifying light weapons, one action, and one bonus action.
5. With automatic dual wielding **off**, make one normal main-hand attack. Save the lines beginning with `[WM55 Nick Debug]`.
6. Reload the same state or start another equivalent turn.
7. With automatic dual wielding **on**, make the same attack. Save the lines again.
8. Enter `!wm55_nick_debug off` when finished.

Use a high-accuracy target if possible. On a hit, `AttackedBy` reports `cause=Offhand`; `MissedBy` does not report the damage cause.

## What to compare

- **Spell identity:** Does the toggle-on run report only `Target_MainHandAttack`, or also another spell?
- **Action identity:** Do the main-hand and off-hand `StartAttack` or `AttackedBy` events share a story action ID?
- **Bonus action:** Compare `bonus=` before and after the toggle-on attack.
- **Nick state:** Check whether `ready=1` remains after the event whose `cause=Offhand`.

The key result is the first toggle-on `AttackedBy` line with `cause=Offhand`, plus the nearest `StatusApplied` and `StatusRemoved` lines.
