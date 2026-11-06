"""Test-only npsim steering for the DD4hep_VolumeAssembly feasibility test.
DD4hep_VolumeAssembly leaves the SD type at the compact default 'sensitive'; treat that type as
a tracker and disable filters for the test plane (pattern RefPlaneVATest)."""
SIM.action.trackerSDTypes = ["tracker", "sensitive"]  # noqa: F821
SIM.filter.mapDetFilter["RefPlaneVATest"] = None  # noqa: F821
