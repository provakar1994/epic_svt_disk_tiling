# Step 8m: regenerate ACTS material map after the three-layer RSU change

Step 8l adds 2.5 um of full-RSU copper and redistributes the 50 um silicon
between inactive and active layers. The pre-Step-8l ACTS material map must
not be treated as a validation of this geometry.

Run `regenerate_svt_material_map_step8m.sh` from the 26.09.0-stable EIC shell
after building and installing this checkout and sourcing
`install/bin/thisepic.sh`. Its defaults are 1000 events x 5000 geantinos;
two optional positive integer arguments select a smaller smoke sample, e.g.
`bash proj_svt_disk_tiling/logs/regenerate_svt_material_map_step8m.sh 10 100`.
The script is prepared but has not been executed.

The wrapper verifies the installed material-map XML includes the SVT module
builder, that the installed module constants match Step 8l, and that the
installed module XML matches the source. It retains the runner's fixed-name
plot directories under `proj_svt_disk_tiling/tmp/retained/` and records moves
in `proj_svt_disk_tiling/tmp/file_actions.log`. Map products use a timestamped
`step8m_` prefix in `scripts/material_map/`; the transcript and checksums go
to `proj_svt_disk_tiling/logs/material_map_step8m_<timestamp>.txt`.

The existing runner validates the regenerated map but skips validation with
the older calibration CBOR because the current ACTS bindings reject that
map's cylinder-axis binning. Review the regenerated plots, transcript, and
the known `envelope26` warning before selecting the produced CBOR with
`-Pacts:MaterialMap=/absolute/path/to/step8m_<timestamp>_material-map_map.cbor`.
