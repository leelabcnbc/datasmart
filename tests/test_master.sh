#!/usr/bin/env bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/..
# second is legacy.
python -m unittest discover -v && python test_filetransfer_remote_mapping.py