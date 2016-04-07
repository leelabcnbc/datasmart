#!/usr/bin/env bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/..
python -m unittest discover -v