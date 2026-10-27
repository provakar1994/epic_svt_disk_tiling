# SVT disk acceptance analysis

This directory contains the simulation campaign and a streaming analysis for
the simulated-hit acceptance of each silicon endcap disk. The analysis keeps
the generated vertex samples at `z = 0`, `-10`, and `+10 mm` separate.

## Definition

For one generated primary pion and one disk, the event is accepted when the
particle has at least one directly associated `TrackerEndcapHits` entry on that
disk. Multiple hits on the same disk count once. The integrated result is

```text
number of selected generated primaries with >=1 disk hit
-------------------------------------------------------- .
       number of selected generated primaries
```

The reader follows the stored hit-to-MCParticle ObjectID. It does not match by
row number and does not infer ancestry. The particle identity is
`(file_id, event_entry, mc_index)`. Use the `sim_*.root` files: the slim
reconstruction outputs do not retain `TrackerEndcapHits`.

## Disk mapping

| Side | Disk | System | Layer | Nominal z [mm] |
|---|---:|---:|---:|---:|
| negative | ED0 | 68 | 1 | -250 |
| negative | ED1 | 69 | 1 | -450 |
| negative | ED2 | 70 | 2 | -650 |
| negative | ED3 | 70 | 3 | -850 |
| negative | ED4 | 70 | 4 | -1020 |
| positive | HD0 | 77 | 1 | +250 |
| positive | HD1 | 78 | 1 | +450 |
| positive | HD2 | 79 | 2 | +700 |
| positive | HD3 | 79 | 3 | +950 |
| positive | HD4 | 79 | 4 | +1200 |

Always identify a disk with `(hit collection, system, layer)`. Several
detectors reuse layer numbers. Nominal z values come from
`compact/tracking/definitions_craterlake.xml`; they are disk centres, not the
median z of hits on the corrugated sensor surfaces.

## 2D-map coordinate convention

A missing hit has no measured `(x,y)`. To put hit and missing-hit events into
the same disk-plane bins, the reducer projects the generated particle from its
production vertex to the nominal disk z:

```text
x_disk = vertex_x + (z_disk - vertex_z) * px/pz
y_disk = vertex_y + (z_disk - vertex_z) * py/pz
```

This is a reference coordinate, not a propagation through the magnetic field.
The reducer saves the RMS difference between this projection and observed hit
positions. Review that diagnostic before interpreting fine spatial structure.
If the residual is comparable to the bin width, use coarser bins or replace the
projection with a field-aware propagator.

The default map spans `-450` to `+450 mm` with `10 mm` square bins. Integrated
acceptance uses every selected primary; the 2D denominator contains particles
whose projected coordinate falls inside the map. Empty or low-statistics bins
are masked by the plotter.

## Two-stage design

ROOT reading and MCParticle-to-hit association are the expensive operations.
Run them once with no eta or momentum cuts:

```text
sim_*.root
    -> extract_disk_particles.py
    -> one compact per-primary NPZ shard per ROOT file
```

Each extracted row retains generated momentum and vertex, eta, a five-bit disk
hit mask, hit multiplicities, and mean observed hit coordinates. Particles with
zero hits remain in the shards, so later cuts do not bias the denominator.

Repeatable analysis then reads only these compact shards:

```text
extracted shards
    -> eta/momentum selection + projection + histogramming
    -> integrated CSV and compact 2D NPZ
```

Changing eta, momentum, map binning, or projection logic therefore does not
reopen the ROOT files. Use a distinct reduction output directory for each cut.

## Files

- `mc_tracking_hits.py`: bounded-memory MCParticle/SimTrackerHit reader.
- `extract_disk_particles.py`: expensive one-time ROOT-to-particle extraction.
- `reduce_disk_acceptance.py`: fast late cuts and NPZ/CSV histogram reduction.
- `validate_disk_acceptance.py`: checks count and shape invariants.
- `validate_reduction_equivalence.py`: compares extracted and ROOT-direct results.
- `plot_disk_acceptance.py`: makes integrated, hit/missing, and 2D maps.
- `disk_acceptance_analysis.ipynb`: interactive steering and visualization.
- `run_disk_acceptance_analysis.sh`: recorded full workflow.
- `run_disk_acceptance_smoke.sh`: recorded 2,000-event end-to-end check.
- `run_disk_acceptance_cut_smoke.sh`: recorded eta/momentum-selection check.
- `run_disk_acceptance_two_stage_smoke.sh`: two reductions from one extraction.
- `run_disk_acceptance_equivalence_check.sh`: exact late-cut/reference comparison.

The extractor never concatenates the campaign's raw events. It reads one ROOT
file in bounded event blocks and writes one independently recoverable shard.
The reducer then streams these substantially smaller shards.

## Interactive notebook

Open `disk_acceptance_analysis.ipynb` to steer the workflow interactively. Its
first code cell controls the reusable extraction, vertices, optional `|eta|`
and momentum cuts, binning, file/event limits, and output locations. Extraction
and reduction have separate explicit run gates. Later cells show both exact
commands, validate outputs, display integrated
tables, make plots, and inspect projection residuals. The notebook invokes the
same scripts documented here, so interactive and batch results cannot silently
use different formulas.

Optional generated-particle selections belong in the reducer:

```bash
--abs-eta-range 1.0 2.5 \
--momentum-range-gev 1.0 10.0
```

Ranges are half-open. The absolute-eta selection becomes `[1.0,2.5)` on the
positive side and `[-2.5,-1.0)` on the negative side. Always use a distinct
output directory for each selection.

## Small validation run

The preferred smoke test extracts 5,000 events from the first file on each side
once, then performs an inclusive and a cut reduction from the same shards:

```bash
./run_disk_acceptance_two_stage_smoke.sh
```

## Full analysis

Run the recorded master script from a suitable compute allocation:

```bash
./run_disk_acceptance_analysis.sh
```

Its default output is `results/acceptance_v1/`. The `extracted/` subtree is the
reusable particle dataset. Each reduction then produces:

- one CSV with the ten integrated disk results and Wilson intervals;
- one compressed NPZ with integrated counters, 2D numerator/denominator arrays,
  projection diagnostics, and input-file provenance;
- one integrated-acceptance plot;
- positive- and negative-side hit/missing plots;
- positive- and negative-side 2D acceptance maps.

The full production validation requires 50 files and 5,000,000 selected events
per eta side. Results from different generated vertices remain separate.
