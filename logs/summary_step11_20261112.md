# Morning summary, Step 11 (night of 2026-11-11 to 11-12)

Full details: `logs/rsu_opt_endcap_20261004.md` (Steps 11a to 11f). Nothing is committed.
Plan for the reruns after this review: `logs/overnight_plan_20261111.md`.

## Result

The delivered placements are used **exactly as supplied**, with no added translations.
**No overlaps** were found in any geometry that was checked:

| Geometry | Modules placed | ROOT 0.01 mm, tracking-only | ROOT 0.01 mm, full craterlake | Geant4 0.1 mm, tracking-only |
|---|---|---|---|---|
| 20261110_ES/rsu_opt (production) | 2164 | 0 | 0 | 0 (PASS) |
| 20261110_ES/rsu6 ("all 6-RSU") | 2150 | 0 | not run | 0 (PASS) |
| 20261110-r_ES/rsu_opt | 2164 | 0 | 0 | 0 (PASS) |
| 20261110-r_ES/rsu6 | 2150 | 0 | 0 | 0 (PASS) |

Source-level validators: 20261110 package 35/35 PASS, -r package 54/54 PASS.
The 7 FPC/end-film pairs found in the old all_6rsu (Step 8d) are gone in rsu6: the provider
re-tiled exactly those 10 rows with 2 modules instead of 3.

## What changed (EPIC repo: `src/SiEndcapModuleTracker_geo.cpp`, `compact/tracking/silicon_disks_modules.xml`)

1. Disk 8 files are named `HD3_*`. The loader falls back to `HD3b_*`, so 20261001 still loads.
2. Catalogue chirality `NEGATIVE`/`POSITIVE` is accepted. It equals the old `RIGHT`/`LEFT`; this was
   checked type by type.
3. `SiEndcapTilingOppositeFacing_z_offset` was changed from 0.230 to 0. The delivery now includes the
   offset itself: every outward module is +0.230 mm off its row's `facet_z`, away from the carbon.
   The 20261001 delivery would still need 0.230.
4. The inactive Si was reduced from 36 to 33.5 um, so inactive Si + active Si (14) + Cu (2.5) = 50 um.
   The Cu now sits inside the 50 um, and `z_sensor_mm` is the plane of the Cu outer face. This is
   noted in the XML.
5. For inward modules only, the bridge FPC is split. The 80 um Kapton stays on the sensor side of
   the baseplate, flush with the 80 um epoxy at the carbon surface. The 30 um Al moves to the back of
   the baseplate, under the same footprint. The AncASIC now sits on the Kapton. Outward modules are
   unchanged. The XML note gives the reason and the provider's suggestion, and that x/X0 is unchanged.
6. `SiEndcapTilingInwardModule_z_clearance` was changed from 0.0325 to 0. It existed only for the
   inward FPC Al.
7. The production XML now selects `20261110_ES/rsu_opt`. rsu6 and -r are loaded through overlay XMLs.

The exported prototype stacks match these changes. For inward B610 the local z in um is:
Al -320..-290, CF -290..-140, epoxy/Kapton -140..-60 (-60 = carbon surface), Cu outer face -30
(= +30 um, matching the CSV). See `logs/inspect_svt_export_step11d.txt`.

## Please review / decide

- **Visual check.**
  - `out/visualize_step11b_rsu_opt.root` and `out/visualize_step11b_rsu6.root`.
  - `out/visualize_step11f_20261110-r_ES_{rsu_opt,rsu6}.root`.
  - Things to look at: inward modules (Al behind the baseplate, Kapton flush with the epoxy) and
    outward modules (gap of 0.23 mm to the carbon).
  - Make more with `logs/make_svt_visualize.sh <step> [scenario | delivery/scenario]`.
- **Corrugation still uses the 20261001 lattice table.** The delivered `<disk>_rows.csv` place the
  A-region channels up to 0.79 mm away from that lattice. The A row spacing is irregular,
  16.53 to 19.23 mm at half pitch 18. This does not cause overlaps now, but it does change where
  the carbon sits. I recommend building the corrugation from `rows.csv` (Step 12) before the material
  map, scan, acceptance and tracking reruns.
- **0.23 mm outward gap.** The validator noticed that 0.230 = 80 um epoxy + 150 um baseplate, as if
  outward modules were referenced to the inward module stack. The provider has not stated this. It may
  be worth confirming what the 0.23 mm represents physically: in the model, the outward external
  epoxy now starts 0.23 mm from the row's `facet_z`, the same position the old code offset gave.
- **rsu6 differs from the old all_6rsu** in 10 rows, which went from 3 modules to 2. HD0 row 3 also
  changed facing.
- **-r package.**
  - Every module is turned over: same row and x-y, opposite facing and chirality, and its sensor
    plane moves 0.60 mm.
  - The per-disk inward/outward imbalance on ED2 and HD1-HD4 reverses.
- The old step validators (e.g. 8l, 8f) hard-code 36 um and the 0.0325/0.230 offsets, so they will
  now fail by design. They were not run.

## Next (after your review), per scenario

12. Build the corrugation from `rows.csv` and rerun the overlap checks.
13. Then, for each scenario: ACTS material map, per-disk material scan, refplane acceptance (hit
    efficiency), and track efficiency. Each map must come from the same XML that the reconstruction
    uses.
