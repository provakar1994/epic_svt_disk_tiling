#!/bin/bash
kmake=$1
kfresh=$2

FLAG=""
if  [ "$kfresh" == 1 ]; then
FLAG="--fresh"
fi
if  [ "$kmake" == 1 ]; then
# cmake --fresh -B build -S . -DCMAKE_INSTALL_PREFIX=install -DEPIC_ECCE_LEGACY_COMPAT=OFF; 
cmake $FLAG -B build -S . -DCMAKE_INSTALL_PREFIX=install -DEPIC_ECCE_LEGACY_COMPAT=OFF; 
cmake --build build -j4; 
cmake --install build;
fi
# source /global/homes/s/shujie/eic_dir/epic/install/setup.sh
# . /global/homes/s/shujie/eic_dir/epic/install/bin/thisepic.sh
. install/bin/thisepic.sh
source install/bin/thisepic.sh
echo "set DETECTOR_PATH="  $DETECTOR_PATH
 #cd install/share/epic


## checkoverlaps
## Tgeo
# checkOverlaps -c ${DETECTOR_PATH}/epic_disk_hole.xml
## ACTS
# python scripts/checkOverlaps.py -c $DETECTOR_PATH/epic_disk_hole.xml 


# dd_web_display --export ${DETECTOR_PATH}/epic_disk_hole.xml
# python ../materialmap_craterlake/geometry_ePIC.py -i $DETECTOR_PATH/epic_disk_hole.xml 
# python3 /global/homes/s/shujie/eic_dir/acts/Examples/Scripts/MaterialMapping/GeometryVisualisationAndMaterialHandling.py --geometry geometry-map.json



# python geometry_ePIC.py -i $DETECTOR_PATH/epic_craterlake.xml 
# python3 ${ACTS}/Examples/Scripts/MaterialMapping/GeometryVisualisationAndMaterialHandling.py --geometry geometry-map.json