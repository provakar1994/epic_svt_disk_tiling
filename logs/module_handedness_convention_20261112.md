# SVT endcap module handedness: tiling convention vs. the Module Definitions PDF

Date: 2026-11-12

This note compares two sources:

- **Tiling package.** Ernst S.'s tiling delivery 20261110: `catalog.csv`, the `<disk>_modules.csv`
  files, and `transition/module_cad_export.py`. This note treats it as the reference.
- **Definitions PDF.** `ES_material/20261016-Module Definitions.pdf`, v1.0, dated 2026-10-16. No
  author is given, and it is a different author from the tiling package. The PDF still calls the
  chirality Left/Right.

The aim is to state the tiling convention completely, then list where the PDF's Left/Right
description agrees with it and where it does not.

## 1. The tiling convention (Ernst S.)

### 1.1 Type ID

A type ID such as `B610` is read as follows:

- **Letter:** the baseplate width. A = 35 mm, B = 32 mm.
- **First digit:** the RSU count, 5 or 6.
- **Second digit:** the facing. 0 = OUTWARD, 1 = INWARD.
- **Third digit:** the chirality. 0 = NEGATIVE, 1 = POSITIVE.

Facing and chirality describe which physical part a module is, not how it is placed. The two
chiralities are mirror-image parts. No rotation turns one into the other.

### 1.2 Placement data (`<disk>_modules.csv`)

- `x_origin_mm`, `y_origin_mm` give the module's local origin. It sits at the boundary between the
  LEC and the first RSU, midway across the sensor. The module extends from there toward x = 0.
- `z_sensor_mm` is the sensor's exposed outer surface.
- `z_baseplate_mm` is the corrugation reference.
- The **face** is FRONT if `z_baseplate_mm` is below the disk's `z_center_mm`, and BACK otherwise.
  This uses global z for both endcaps. The CAD script also reports the face relative to the IP
  (TOWARD_IP / AWAY_FROM_IP).
- **Facing:** OUTWARD means the sensor faces away from the disk mid-plane. INWARD means it faces
  toward the mid-plane, i.e. toward the carbon.

### 1.3 Orientation and chirality rule

This is taken from `module_cad_export.py`. Each placed module has three local axes, and each one
points along plus or minus a global axis:

| local axis | physical meaning | global sign |
|---|---|---|
| x | from the LEC toward the REC | `sx = -sign(x_origin)`, i.e. toward the disk centre |
| y | away from the disk's y = 0 line | `sy = +sign(y_origin)` |
| z | out of the sensor, away from the carbon | `sz = -face_sign * facing_sign` |

- `face_sign` is +1 for FRONT and -1 for BACK.
- `facing_sign` is +1 for OUTWARD and -1 for INWARD.
- `sign(v)` is +1 if v > 0 and -1 otherwise, so a row exactly at y = 0 counts as y < 0.

The chirality follows from these signs:

```
POSITIVE  <=>  sx * sy * sz = +1
NEGATIVE  <=>  sx * sy * sz = -1
```

- In this frame, x and z are tied to the part itself, but y is tied to the disk (away from y = 0).
  So the frame is right-handed for a POSITIVE part and left-handed for a NEGATIVE part.
- Every module in the 20261110 and 20261110-r deliveries obeys this rule. That covers all
  scenarios: 2164 modules in rsu_opt and 2150 in rsu6.

### 1.4 CAD rotations

The CAD export gives each module a rotation (`Rx`, `Ry`, `Rz`) applied to the part's own
reference pose.

- **POSITIVE part:** the signs (sx, sy, sz) are used directly. Their product is +1, so they
  describe a proper rotation.
- **NEGATIVE part:** all three signs are negated first.
- The resulting signs are converted as follows:
  - (+,+,+) is the identity.
  - (+,-,-) is Rx(180°).
  - (-,+,-) is Ry(180°).
  - (-,-,+) is Rz(180°).

### 1.5 Where the bridge FPC goes

The CAD script does not mention the FPC, so this section combines the tiling rule with the PDF
drawings.

- **Slide 9:** this module is POSITIVE by the tiling rule (section 2), and the PDF draws its FPC
  toward +y.
- **POSITIVE part:** its FPC therefore lies on +y of its right-handed frame, where x points toward
  the REC and z points away from the carbon. The tiling placement points that +y away from y = 0.
- **NEGATIVE part:** its FPC is on -y of its right-handed frame. Its placement points that
  right-handed +y toward y = 0, so its FPC also ends up pointing away from y = 0.

So the rule is the same everywhere: **every bridge FPC points away from the disk's y = 0 line, for
both chiralities, on every face.** The two disk halves are mirror images of each other in y.

Together with the LEC sitting at the outer end and the facing setting the sensor direction, this
fixes the chirality of every slot. PDF slide 7 shows the same thing: on the top half of the ED1
back face, all FPC tails point up.

## 2. Worked example: ED1, back face, top half (PDF slides 7-12)

ED1 has `z_center` = -450 mm. The back face is the one at larger z, so `face_sign` = -1, and the
top half has `sy` = +1. The four module slots in the PDF are:

| PDF slide | slot | tiling signs (sx, sy, sz) | tiling chirality | example type in 20261110 rsu_opt (count on this face/half) | tiling CAD rotation | PDF signs | PDF label |
|---|---|---|---|---|---|---|---|
| 9  | x < 0, OUTWARD | (+1, +1, +1) | POSITIVE | B501 (17) | none | (1, 1, 1) | Left |
| 10 | x < 0, INWARD  | (+1, +1, -1) | NEGATIVE | B610 (12) | Rz 180° | (1, -1, -1) | Left |
| 11 | x > 0, OUTWARD | (-1, +1, +1) | NEGATIVE | B600 (11) | Rx 180° | (-1, -1, 1) | Left |
| 12 | x > 0, INWARD  | (-1, +1, -1) | POSITIVE | B511 (21) | Ry 180° | (-1, 1, -1) | Left |

The delivered ED1 file contains exactly these four combinations on this face and half, with the
chirality the rule predicts.

## 3. Where the PDF clashes with the tiling convention

### 3.1 Every slide is labelled "Left" (slides 9-12)

- Each of slides 9-12 says "sx·sy·sz = 1 → Left Chirality".
- The PDF builds its signs from a right-handed module frame, so the product is the determinant of
  a rotation. It is +1 for every orientation and cannot tell the chiralities apart.
- By the tiling rule, slides 9 and 12 are POSITIVE and slides 10 and 11 are NEGATIVE. At least two
  of the four labels are therefore wrong whatever naming is used.

### 3.2 The Left/Right naming points both ways

- **Slide 13** proposes that an FPC toward +y is "right handed" and an FPC toward -y is "left
  handed". Section 1.5 shows that POSITIVE parts have their FPC at +y, so this gives
  POSITIVE = Right and NEGATIVE = Left.
- **The earlier tiling catalogue** (20261001) used POSITIVE = LEFT and NEGATIVE = RIGHT, for
  example A601 LEFT and A600 RIGHT.
- **Slide 9** shows a POSITIVE part with its FPC at +y and labels it "Left", which matches the old
  catalogue but contradicts slide 13.

The PDF's Left/Right is therefore ambiguous, and this is presumably why the tiling package
switched to POSITIVE/NEGATIVE. **Use POSITIVE/NEGATIVE only.** If Left/Right has to be mentioned,
state which mapping is meant.

### 3.3 Frames: one fixed frame (PDF) versus a frame that depends on chirality (tiling)

- **PDF:** slides 3-4 define a single right-handed module frame for every part: x toward the REC,
  z away from the carbon, origin at the LEC/RSU border. The direction of the FPC "does not change
  the local coordinate system". Chirality then shows up as the FPC lying at +y or -y.
- **Tiling package:** local y points toward the FPC, i.e. away from y = 0, so the frame is
  left-handed for NEGATIVE parts (section 1.3).
- The two descriptions agree on the physical layout. The difference matters for the CAD rotations
  of NEGATIVE parts, described next.

### 3.4 The reference pose of NEGATIVE parts in the CAD rotations

- **POSITIVE parts:** the tiling rotations and the PDF's rotations agree. Slide 9 is the identity
  in both, and slide 12 is Ry(180°) in both.
- **NEGATIVE parts:** they differ by an extra Ry(180°).
  - Slide 10: tiling Rz(180°), PDF Rx(180°).
  - Slide 11: tiling Rx(180°), PDF Rz(180°).
- **The tiling convention's NEGATIVE reference pose** is the POSITIVE reference pose inverted
  through the origin (all three axes reversed). In that pose the LEC is on the +x side and the
  sensor faces -z.
- **The PDF's NEGATIVE reference pose** (slide 4, lower module) is the POSITIVE pose mirrored in y
  only. There the LEC stays on the -x side and the sensor faces +z.

**Consequence:** suppose a NEGATIVE CAD part is drawn in the PDF's reference pose and then given
the tiling rotation. It ends up turned 180° about y, with its LEC at the inner end and its sensor
facing the carbon. Whoever builds the CAD assembly should model NEGATIVE parts in the tiling
package's reference pose, or add Ry(180°) to their rotations.

### 3.5 Points that agree

- **Origin:** the PDF puts it at the LEC/RSU border. The tiling package uses the same point,
  midway across the sensor in y and at its exposed surface in z.
- **Local x** points toward the REC, and **local z** points away from the carbon fibre.
- **Back face** means the face at larger global z (slide 7, and the FRONT/BACK test in the CAD
  script).
- **The FPC direction** is the same in both for the four ED1 slots (section 1.5).

### 3.6 Open point: the direction of global x

- **PDF frame:** right-handed, with y up and the electron endcap (ED) at -z (slides 2 and 6). This
  is the same as the EPIC global frame.
- **Tiling openings:** the beam-pipe openings in the tiling metadata are displaced to -x on ED3/ED4
  and to +x on HD2-HD4. That is the opposite x side from the EPIC beam pipe.
- **In EPIC:** we therefore load the tiling package with x_EPIC = -x_tiling and swap the chirality.
  A pure x-mirror reverses the chirality, so this keeps every placement physically consistent.
- **Consequence:** the EPIC model is the x-mirror of the tiling layout as written. Either the
  tiling package's x axis or its beam pipe is reversed relative to the PDF/EPIC frame. **This needs
  confirming with Ernst** before module positions or IDs are compared one-to-one with the CAD.

## 4. Status in the EPIC model

Audit: `logs/check_svt_handedness_step13.{sh,txt}`.

- **LEC side and sensor facing** agree with the tiling convention for 100 % of modules, in all four
  geometries. Mapped through the x-mirror, the built chirality matches the type IDs.
- **Bridge-FPC direction.** Before Step 13b the model pointed every FPC toward global -y, which
  was reversed for all modules at y > 0 (1077 of 2164 in rsu_opt). Fixed in Step 13b: every FPC
  now points away from y = 0. Audit after the fix: 100 % in all four geometries (rsu_opt y>0
  1077/1077, y≤0 1087/1087), 0 overlaps (ROOT 0.01 mm, Geant4 0.1 mm).
- **Type names (known, not changed).** Because of the x mirror (section 3.6), each module is
  placed at the mirror slot and built as the mirror part, but its volume keeps the delivered
  type ID. So in EPIC the chirality digit of every name is the opposite of the physical part
  (xx0 ↔ xx1, e.g. a volume named B600 is physically a B601-type part at its EPIC slot). The
  geometry follows the tiling rule in the EPIC frame; only the names differ. Decision deferred
  until Ernst answers section 3.6 (options: flip the last digit, or drop the x mirror).


## Additional notes from PD - 20261112

Every chirality pair is swapped in the built model, so 610↔611 is swapped too, and so are all the other xx0↔xx1 pairs. Two caveats:

Slide numbers. In my table, 600 and 601 are both OUTWARD, so they correspond to slides 9 and 11, not 9 and 10. Slide 10 is x<0 INWARD and slide 11 is x>0 OUTWARD. The 610/611 pair corresponds to slides 10 and 12. Your conclusion stands either way.

Cause. The swap comes from how the delivery is mirrored into EPIC (x_EPIC = -x_engineer):

The mirror moves each module to the mirror-image slot and builds it as the mirror-image part, so its physical chirality flips.
The volume keeps the type ID from the delivery CSV. The audit confirms this: it matched every placed volume to a CSV row with the same name and found that the built chirality is the opposite of that name's chirality in 100% of modules.
Take the ED1 back face, top half, at EPIC x<0, OUTWARD:

The part that lands there comes from the delivered x>0 OUTWARD slot, which is B600.
After mirroring, it is built physically POSITIVE. Its FPC points away from y = 0, its LEC is at the outer end, and it faces outward, which matches slide 9.
So the geometry at that slot is right by Ernst's rule in the EPIC frame. Only the name's last digit is wrong: it says 600 where the part is physically a 601.
The name and the physical part also disagree in the other direction. In Ernst's own frame, slide 9 is B501, a 5-RSU module. The slot we fill comes from his x>0 side, which carries a 6-RSU module because the beam-pipe opening is off-centre. So a direct name comparison against his figures also picks up differences in RSU count, not just in chirality.

Fix options. I haven't implemented either.

Rename to the mirror partner. Flip the last digit of the type ID when building from the mirrored delivery, so the name matches the physical part in EPIC. The width letter and RSU count stay the same, so the dimensions don't change. The FPC fix stays as it is. This is cheap, but names would no longer match the CSV one-to-one. The audit script and anything else that keys on the type name, such as hit-map plots, would need the same flip.
Drop the x mirror. This only works if Ernst confirms that his x axis is EPIC's x (open point 3.6). If so, names and positions match his package directly. But his beam-pipe openings would then sit on the opposite side from the EPIC beam pipe, so the layout would no longer fit EPIC's beam pipe.
I'd ask Ernst about 3.6 first, because his answer decides between 1 and 2. If you want consistent names now, option 1 is a small change. Should I implement it, or wait for Ernst?

Questions for Ernst:

- Global x direction. His beam-pipe openings are x-mirrored relative to EPIC. Is his x reversed, or is his beam pipe? This is the main question, and it decides between the two naming fixes from my last message.
- FPC direction. Can he confirm that every bridge FPC points away from y = 0? I inferred this from his rule plus the PDF drawings, because his script never mentions the FPC.
- NEGATIVE parts in CAD. What reference pose does he use for them: point inversion or y-mirror?