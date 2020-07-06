openMVG_main_SfMInit_ImageListing -i ./ -d /opt/openmvg/share/openMVG/sensor_width_camera_database.txt -o ./matches/ -c 2
openMVG_main_ComputeFeatures -i ./matches/sfm_data.json -o ./matches/ --describerPreset $1
openMVG_main_ComputeMatches -i ./matches/sfm_data.json -o ./matches/ --force=1 -g $2
openMVG_main_GlobalSfM -i ./matches/sfm_data.json -o ./reconstruction/ -m ./matches/
openMVG_main_openMVG2openMVS -i ./reconstruction/sfm_data.bin -d ./sfm/ -o ./sfm/scene.mvs
DensifyPointCloud ./sfm/scene.mvs
ReconstructMesh ./sfm/scene_dense.mvs