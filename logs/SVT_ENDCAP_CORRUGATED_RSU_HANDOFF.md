# Handoff Note: SVT Endcap Corrugated RSU Module Geometry

We are working in the `epic` detector codebase, specifically the SVT endcap module geometry.

## Important Current Files

- Main geometry implementation:
  - `src/SiEndcapModuleTracker_geo.cpp`
- Compact XML for module-based silicon disks:
  - `compact/tracking/silicon_disks_modules.xml`
- Current corrugation-aware placement CSV:
  - `compact/tracking/SVT_endcap_modules_corrugation_all.csv`
- Barrel RSU reference/example:
  - `compact/tracking/vertex_barrel.xml`
  - `src/CurvedBarrelTracker_geo.cpp`
  - `src/BarrelTrackerWithFrame_geo.cpp`

Note: Older discussion referred to `TileEndcapTracker_geo.cpp`, but in this checkout that file does not exist. The equivalent/current file is `SiEndcapModuleTracker_geo.cpp`.

## Current Code Shape

`SiEndcapModuleTracker_geo.cpp` defines hard-coded module templates in `builtin_module_templates(...)`.

Currently supported module names:

```cpp
EIC_LAS_6RSU
EIC_LAS_5RSU
```

with simplified rectangular dimensions:

```text
EIC_LAS_6RSU: 130.0 mm x 30.0 mm
EIC_LAS_5RSU: 105.0 mm x 30.0 mm
```

The current module stack is simple:

```text
CarbonFiber sheet, passive
Glue, passive
Silicon sensor, sensitive
```

Only the silicon sensor should be an active/sensitive volume.

The placement CSV names module types and gives module positions. The CSV should remain placement data only.

## Current Incremental Implementation Status

A first small implementation step has been made in `src/SiEndcapModuleTracker_geo.cpp`:

- `ComponentTemplate` now has `x_repeat`.
- `ComponentTemplate` now also has `rsu_pattern`.
- `build_module_prototype(...)` can place one component layer as a rectangular RSU pattern along local `x`.
- `EIC_LAS_6RSU` now uses `x_repeat = 6` and `rsu_pattern = true` for its silicon component.
- The RSU-pattern layer places passive backbone, bias, and readout boxes plus one active silicon box per RSU.
- The module thickness is still counted once for the silicon sensor layer, so this creates six side-by-side active RSU sensor volumes rather than six stacked sensor layers.
- `EIC_LAS_5RSU` is still unchanged and has one full-width sensitive sensor volume.
- `compact/tracking/silicon_disks_modules.xml` now defines the RSU constants borrowed from the barrel RSU model:
  - `SiEndcapRSU_width`
  - `SiEndcapRSU_length`
  - `SiEndcapRSU_periphery_width`
  - `SiEndcapRSU_bias_width`
  - `SiEndcapRSU_backbone_width`

This is intentionally not yet the full `EIC_LAS_6RSU_CORR` implementation. It is a first rectangular adaptation of the `CurvedBarrelTracker_geo.cpp` RSU idea.

## Naming Decision

Keep standard EIC-LAS nomenclature.

Preferred new detailed/corrugated module names:

```text
EIC_LAS_6RSU_CORR
EIC_LAS_5RSU_CORR
```

Meaning:

```text
EIC_LAS = standard module/sensor family
6RSU / 5RSU = number of RSU sections
CORR = corrugated-support/endcap-packaged version
```

Do not replace/remove `EIC_LAS_6RSU` and `EIC_LAS_5RSU` at first. Add the new names alongside them for safer incremental testing.

## Geometry Intent

The new corrugated modules should represent full physical module envelopes, not just active sensor rectangles.

Latest module dimension model from user:

```text
Module length =
  0.5 mm
+ LEC FPC width, e.g. 10 mm
+ 0.5 mm
+ LEC
+ n * RSU
+ REC
+ 0.5 mm
+ REC FPC width, e.g. 4 mm
+ 0.5 mm
```

Module width:

```text
Depends on corrugation pitch/angle/radius of curvature.
Current assumption: 32 mm
```

Module thickness assumptions:

```text
RSU/sensor region:
  Si: 50 um
  CF: 150 um
  adhesive: 60-100 um
  total: 260-300 um

FPC/readout region:
  FPC: 115 um
  CF: 150 um
  adhesive: 60-100 um
  total: 325-365 um
```

The `32 mm` width is not intrinsic EIC-LAS active sensor width. It is a corrugation/support-driven envelope width.

## Implementation Strategy

Go slowly and minimally.

### Step 1: Add New Module Types

In `builtin_module_templates(...)`, eventually add something like:

```cpp
module_templates.emplace("EIC_LAS_6RSU_CORR", build_corrugated("EIC_LAS_6RSU_CORR", 6));
module_templates.emplace("EIC_LAS_5RSU_CORR", build_corrugated("EIC_LAS_5RSU_CORR", 5));
```

Keep existing `EIC_LAS_6RSU` and `EIC_LAS_5RSU`.

### Step 2: Add XML Constants

In `compact/tracking/silicon_disks_modules.xml`, add constants for the new geometry, likely near existing endcap module constants:

```xml
<constant name="SiEndcapRSU_length" value="21.67*mm"/>
<constant name="SiEndcapModule_width_corrugated" value="32.0*mm"/>
<constant name="SiEndcapLeftBridgeFPC_width" value="10.0*mm"/>
<constant name="SiEndcapRightBridgeFPC_width" value="4.0*mm"/>
<constant name="SiEndcapModuleEndClearance" value="0.5*mm"/>
<constant name="SiEndcapSensor_thickness" value="50*um"/>
<constant name="SiEndcapAdhesive_thickness" value="80*um"/>
<constant name="SiEndcapModuleCF_thickness" value="150*um"/>
```

Still needed from user/design:

- exact `LEC` length
- exact `REC` length
- material choice for LEC/REC/FPC if not already defined
- whether LEC/REC should be represented as chip boxes, FPC boxes, or both

### Step 3: Extend Component Placement

Current `ComponentTemplate` has:

```cpp
double x_override;
double y_override;
```

but no per-component position offsets. Every component is placed at module center.

Need to extend it with:

```cpp
double x_offset{0.0};
double y_offset{0.0};
```

Then in `build_module_prototype(...)`, change component placement from:

```cpp
Position(0, 0, z_position)
```

to:

```cpp
Position(component.x_offset, component.y_offset, z_position)
```

This enables passive LEC/FPC/REC rectangles at module ends.

### Step 4: Sensitive Volume Rule

Only silicon sensor/RSU active region should be sensitive.

Passive components:

- CF
- adhesive
- FPC
- LEC/REC chips/readout structures
- periphery/readout strips

Sensitive component:

- silicon active sensor region only

Do not call `setSensitiveDetector`, add `PhysVolID("sensor", ...)`, or create a `VolPlane` for passive readout/chip/FPC components.

### Step 5: Placement CSV

Do not update the full CSV immediately.

Eventually, placement rows should use:

```csv
EIC_LAS_6RSU_CORR
EIC_LAS_5RSU_CORR
```

instead of:

```csv
EIC_LAS_6RSU
EIC_LAS_5RSU
```

But first test with a small subset of rows.

The user expects to re-optimize module placement later, so it is okay if the current placement CSV becomes imperfect once full physical envelopes are modeled.

## Design Caveats

Changing module dimensions affects placement rejection. The code uses module `x_size` and `y_size` to check disk containment and beampipe opening intersections.

If `EIC_LAS_6RSU_CORR` is wider/longer than old `EIC_LAS_6RSU`, some rows may be skipped until the placement CSV is re-optimized.

## Reference From Barrel

The vertex barrel RSU implementation is a useful conceptual reference:

- `vertex_barrel.xml` declares RSU-like module components.
- `CurvedBarrelTracker_geo.cpp` special-cases `name="RSU"` and builds active + inactive regions.
- Only the active silicon tile is sensitive.
- Readout/biasing/backbone regions are passive.

For endcap modules, copy the idea, not the curved `Tube` implementation. Endcap modules are rectangular `Box` volumes.

## Recommended First Coding Step

Make the smallest useful change:

1. Add `x_offset`/`y_offset` to `ComponentTemplate`.
2. Update `build_module_prototype(...)` to use offsets.
3. Add `EIC_LAS_6RSU_CORR` / `EIC_LAS_5RSU_CORR` templates.
4. In those templates, build:
   - one passive CF region
   - one sensitive silicon active RSU strip
   - simple passive FPC/readout rectangles at ends
5. Change only a few placement CSV rows to test the new module names.
