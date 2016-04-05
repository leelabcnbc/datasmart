#!/usr/bin/env bash

# this is the location of MATLAB. Here it's set to be that for a R2012b version on Linux.
MATALB_EXECUTABLE="/usr/local/MATLAB/R2012b/bin/matlab"

# extract sac batch
rm -rf SAC_batch
mkdir SAC_batch
tar -xzvf SAC_batch.tar.gz -C SAC_batch .

# extract spike sort
rm -rf spikesort
mkdir spikesort
tar -xzvf spikesort.tar.gz -C spikesort .

# get MATLAB configuration
${MATALB_EXECUTABLE} -nodisplay -nosplash -r "ver; exit;" > system_info 2>&1
# run sac batch
${MATALB_EXECUTABLE} -nodisplay -nosplash -r "sacbatch_script; exit;" 2>&1 | tee sacbatch_output
# pause
read -p "press enter to continue"
# run spikesort
${MATALB_EXECUTABLE} -r "spikesort_script;"

echo 'done'
