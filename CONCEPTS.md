# Concepts and conventions (project-wide)

Short explanations of physics, analysis and software concepts met in this project.
Progress and results belong in the study logs; this file only explains ideas.
Add new entries at the end of the relevant section, with the date and the study
where the concept came up.

---

## Tracking basics

### Track parameters (ACTS / edm4eic) — 2026-11-06, tracking performance study
A reconstructed track is described by six numbers at a reference surface:
`loc.a`, `loc.b` (position on the surface), `phi`, `theta` (direction), `q/p`
and `time`. In EICrecon, `CentralCKFTrackParameters` are given at the **perigee**:
the point of the track closest to the beam line (z axis), measured from the
origin (0, 0, 0). Units: mm, rad, e/GeV, ns.

### q and q/p — 2026-11-06, tracking performance study
- **q** is the electric charge of the particle in units of e (+1 for pi+, -1 for pi-).
- **q/p** is charge divided by momentum [e/GeV]. It is a track parameter instead
  of p because it is what the tracker actually measures: in the solenoid the
  track curvature is 1/R = 0.3 * B[T] * q / pT[GeV] [1/m]. The hits measure
  the bend (sagitta), the Kalman fit turns it into q/p, and the measurement
  errors (hit resolution, multiple scattering) smear q/p roughly symmetrically,
  so its residuals are close to Gaussian. The sign of q/p gives the charge.

### Why dp/p becomes skewed when the resolution is large — 2026-11-06, tracking performance study
p is computed, not measured: p = 1/|q/p|. Write the measured value as
q/p = (q/p)_true * (1 + eps), with eps Gaussian of width sigma. Then

    dp/p = 1/(1 + eps) - 1 = -eps + eps^2 - ...

- Small sigma (few %): dp/p ~ -eps, so dp/p and d(q/p)/(q/p) have the same width.
- Large sigma (tens of %): the transformation is lopsided. For sigma ~ 25%,
  eps = +0.5 gives dp/p = -33% but eps = -0.5 gives +100%. A symmetric q/p
  spread becomes a compressed low side with a sharp edge and a long high tail.
- A Gaussian-core fit to that skewed shape is unstable: the fitted sigma can
  jump between neighbouring momentum bins (seen as a "kink" in
  -3.5 < eta < -3.0: dp/p 22 -> 28 -> 32% over 8-11 GeV, while d(q/p)/(q/p)
  goes smoothly 15 -> 16 -> 17%).
- Rule: quote **d(q/p)/(q/p)** where the resolution exceeds ~8-10%. It equals
  dp/p to first order, so it is a fair comparison with sigma_p/p requirements.
  It does not improve the detector; it makes the number trustworthy.

### DCA (distance of closest approach) — 2026-11-06, tracking performance study
How far the reconstructed track passes from the true production point.
- **DCAr** = `loc.a` at the perigee: signed transverse distance to the beam line.
  For a gun at x = y = 0 the true value is 0, so DCAr itself is the residual.
- **DCAz** = `loc.b - vz_true`: longitudinal offset at the point of closest approach.
- Measures how well tracks point back to the vertex (vertexing, heavy-flavour
  tagging). PWG requirement is given vs pT: sigma = a/pT (+) b [um].

### Track covariance (edm4eic Cov6f) — 2026-11-06, tracking performance study
The 6x6 symmetric covariance of the track parameters is stored as 21 numbers
(lower triangle). Basis order follows ACTS: [l0, l1, phi, theta, q/p, t]
(note: phi before theta). Diagonal element (i,i) is at index i + i*(i+1)/2:
var(loc.a)=cov[0], var(loc.b)=cov[2], var(phi)=cov[5], var(theta)=cov[9],
var(q/p)=cov[14], var(t)=cov[20]. Verified against the edm4eic 8.10 header
(`Cov6f.h`) in eic_xl 26.09.0-stable.

---

## Analysis methods

### Resolution and pull — 2026-11-06, tracking performance study
- **Resolution**: width of (reconstructed - true). Tells how precise the tracker is.
- **Pull**: (reconstructed - true) / (error the fit reports). If the fit's
  errors are correct, the pull is a unit Gaussian (mean 0, width 1).
  Width > 1: errors underestimated (e.g. material or misalignment not fully
  modelled, wrong material map). Width < 1: errors overestimated.
  Mean != 0: bias.

### Gaussian-core fit — 2026-11-06, tracking performance study
Resolution distributions have non-Gaussian tails (hard scatters, wrong hits),
so the width is taken from a Gaussian fitted to the core only. Algorithm
(Shujie's `hist_gaus`): start from median and 1.4826 * MAD (median absolute
deviation; 1.4826 makes it equal to sigma for a Gaussian), iterate with a
+/- 3 scale window, then fit a Gaussian to a 101-bin histogram in that window.
Always check the fit-check plots: the result is only meaningful if the core is
roughly symmetric (see the dp/p skew entry above).

### Tracking efficiency — 2026-11-06, tracking performance study
(generated primaries with >= 1 associated reconstructed track) / (generated
primaries), primaries = `generatorStatus == 1`, charged. Association uses the
MC-truth link `CentralCKFTrackAssociations`; each primary counted once.
Binomial errors use the Wilson interval, which stays sensible at eff near 0 or 1.

---

## Detector conventions

### Backward / forward, eta sign — 2026-11-06, tracking performance study
ePIC: electron beam travels toward -z, hadron beam toward +z.
- **backward** = eta < 0 = electron-going endcap = ED disks (ED0-ED4).
- **forward** = eta > 0 = hadron-going endcap = HD disks (HD0-HD4).
- eta = -ln(tan(theta/2)); theta = 90 deg is eta = 0.

### PWG momentum-resolution requirements — 2026-11-06, tracking performance study
From the ePIC preTDR v2.1 sec. 8.3.3 (table copied in
`simrec/treffi_study/pwg_requirements.txt`): sigma_p/p [%] = A*p (+) B, with
(+) meaning sqrt of sum of squares. A*p is the measurement (curvature) term,
growing with p because stiffer tracks bend less; B is the multiple-scattering
term, constant in p.

| eta region | A [%/GeV] | B [%] |
|---|---|---|
| -3.5 to -2.5 | 0.10 | 2.0 |
| -2.5 to -1.0 | 0.05 | 1.0 |
| -1.0 to 1.0 | 0.05 | 0.5 |
| 1.0 to 2.5 | 0.05 | 1.0 |
| 2.5 to 3.5 | 0.10 | 2.0 |
