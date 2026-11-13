"""npsim steering file for the SVT disk reference-plane overlay (Step 9e, 2026-11-06).

Use together with the overlay geometry:
  npsim --compactFile refplanes/generated/epic_craterlake_tracking_only_refplanes.xml \
        --steeringFile refplanes/npsim_refplanes_steering.py  <usual gun/output options>

What it changes (and only this):
  The reference planes are Vacuum, so every plane step has zero energy deposit.
  npsim.py sets the default tracker filter to 'edep0' (EnergyDepositMinimumCut, Cut = 0),
  and ddsim's own default is 'edep1kev'; either would drop all plane hits. DDSim's
  Filter.applyFilters() attaches the filters of any mapDetFilter pattern that is a
  case-insensitive SUBSTRING of the sensitive-detector name (= detector name) and then
  skips the default filter. Mapping the pattern 'SVTDiskRefPlanes' to None (-> []) therefore
  removes all filters from SVTDiskRefPlanesP and SVTDiskRefPlanesN only. No other
  detector name contains this substring, so TrackerEndcapHits and every other tracker
  keep npsim's default filter.

Important: do NOT create a new DD4hepSimulation() here. DD4hepSimulation.readSteeringFile()
pre-binds SIM to npsim's own RUNNER object; a fresh DD4hepSimulation would replace RUNNER's
settings (for example part.userParticleHandler = 'Geant4TVEicParticleHandler', set by npsim
before the steering file is read) with plain ddsim defaults.
"""

REFPLANE_SD_PATTERN = "SVTDiskRefPlanes"

SIM.filter.mapDetFilter[REFPLANE_SD_PATTERN] = None  # noqa: F821  (SIM is provided by npsim)
