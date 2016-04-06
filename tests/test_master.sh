#!/usr/bin/env bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/..
python test_filetransfer.py
python test_filetransfer_remote_mapping.py
