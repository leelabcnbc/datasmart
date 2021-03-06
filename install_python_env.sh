#!/usr/bin/env bash

# first, install an empty Python 3 environment.
conda create -y --name datasmart python=3
# then, activate environment.
. activate datasmart
# then install everything needed.
pip install -r requirements.txt

# then install those visualization related stuff. not needed for travis, but good for everyday use.
conda install -y -c conda-forge pandas notebook numpy
