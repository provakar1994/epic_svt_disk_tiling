# Overnight plan 2026-11-11 -> 11-12: adopt the 20261110 delivery (Step 11)

Delivery staged in Step 11a: `compact/tracking/silicon_disks_tiling/20261110_ES/{rsu_opt,rsu6}`
(transition variant). "all_6rsu" in requests = `rsu6` in this delivery.

## Facts established before starting (Step 11a follow-up checks)

- Module x, y, type unchanged vs 20261001 (rsu_opt). Outward modules: z_baseplate and z_sensor
  shifted by +0.230 mm along the module normal (away from carbon) for all 1109 (rsu_opt) / 1104
  (rsu6) outward modules = exactly the code's current provisional `SiEndcapTilingOppositeFacing_z_offset`.
  Inward: z_baseplate == row facet_z.
- `<disk>_rows.csv`: row_y == module y_origin exactly; identical for rsu_opt and rsu6. In the A
  (half-pitch 18 mm) region rows deviate up to 0.79 mm from the regular lattice in
  `20261001_ES/SVT_endcap_corrugation_rows_33_36.csv` (ED4/3/2, HD2/3/4); 6-7 BLOCKED rows per disk.
- Inward FPC conflict (Step 8e/8q review): inward Kapton spans -80..0 um, Al 0..+30 um relative to the
  corrugation surface; the Al sits inside the neighbouring flat. This is why the -0.0325 mm inward
  translation exists.

## Overnight (Step 11b-11e)

11b. Code + XML (`src/SiEndcapModuleTracker_geo.cpp`, `compact/tracking/silicon_disks_modules.xml`):
  1. Disk 8 file name `HD3` (fallback `HD3b` for the 20261001 delivery).
  2. Catalogue chirality `NEGATIVE`/`POSITIVE` (= old `RIGHT`/`LEFT`, verified per type_id); old labels still accepted.
  3. `SiEndcapTilingOppositeFacing_z_offset` -> 0 (offset now in the data; note that 20261001 needs 0.230).
  4. RSU stack: inactive Si 36 -> 33.5 um so inactive + active (14) + Cu (2.5) = 50 um; Cu inside the
     50 um; CSV z_sensor_mm = plane of the Cu outer face. XML note.
  5. Bridge FPC split for INWARD modules only: 80 um Kapton stays on the sensor side of the baseplate,
     30 um Al moves to the back (outer) side of the baseplate. Outward modules unchanged (their back
     side carries the external epoxy on the carbon). AncASIC sits on the Kapton. XML note.
  6. `SiEndcapTilingInwardModule_z_clearance` -> 0. The delivered placements are then used as-is.
  7. Production XML selects `20261110_ES/rsu_opt`; rsu6 tested through a generated overlay XML.
  Corrugation stays on the 20261001 lattice table tonight (rows.csv adoption = Step 12, below).
11c. Source-level validator (Python, helper agent): delivery consistency, z references with the new
  stack, FPC/REC-film pair audit for both scenarios (the old all_6rsu had 7 such pairs), inward
  Kapton/Al vs carbon intervals.
11d. Build/install, dd_web_display export, ROOT checkOverlaps (option m, 0.01 mm) on tracking-only
  for rsu_opt and rsu6 (and full craterlake for rsu_opt).
11e. Geant4 overlap checks (0.1 mm) for both scenarios as Slurm jobs; visualization ROOT files for
  both scenarios. Detailed log entries in `rsu_opt_endcap_20261004.md`; morning summary
  `logs/summary_step11_20261112.md`. No commit until reviewed.

## After the morning review (not overnight)

12. (Recommended first) Build the corrugation from the delivered `<disk>_rows.csv` (row_y, facet_z,
    half_pitch, BLOCKED) instead of the reconstructed lattice; it moves carbon by up to 0.79 mm in
    the A region and therefore changes material. Rerun overlaps. Otherwise every rerun below is
    redone after this change.
13. Choose the production scenario (rsu6 likely). Every item below is per scenario, since the ACTS map
    must come from the same XML used in reconstruction:
    a. ACTS material map (`logs/regenerate_svt_material_map_step8q.sh` adapted, Slurm, ~80 min each).
    b. Per-disk material scan (`run_svt_disk_material_scan_step8q.sh` adapted) + comparison to 8q.
    c. Reference-plane acceptance / hit efficiency (`acceptance_v3_refplanes` campaign recipe:
       regenerate refplane overlay XML, npsim, analysis) for rsu_opt and rsu6.
    d. Track efficiency/resolution (`simrec/treffi_study`) on 13c output with the matching map.
