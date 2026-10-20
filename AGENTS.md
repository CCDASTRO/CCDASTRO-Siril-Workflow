# Project boundaries

This is an independent CCDASTRO development port. Work only within this project for port changes. Do not edit the PixInsight-Workflow-Manager repository, PI signing files, manifest or release artifacts. Do not introduce a runtime dependency on the PI project or on the other host port.

Preserve source images and metadata; process copies and require explicit candidate acceptance. Keep host-native commands allowlisted. Never bundle proprietary plugins, model weights, credentials or license files. Update README scope and verification records to reflect actual tested behavior. Run the unit suite after processing or adapter changes. Keep helper modules prefixed with an underscore so SASpro's recursive script discovery does not expose them as scripts.
