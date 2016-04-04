# DataSMART

[![Build Status](https://travis-ci.org/leelabcnbc/datasmart.svg?branch=master)](https://travis-ci.org/leelabcnbc/datasmart) [![Documentation Status](http://readthedocs.org/projects/datasmart/badge/?version=latest)](http://datasmart.readthedocs.org/en/latest/?badge=latest)

DataSMART is design to manage data and processing pipelines in science labs.

This project is under heavy development...

## Installation

1. Install [Anaconda](https://anaconda.org/) or [Miniconda](http://conda.pydata.org/miniconda.html).
   Versions for 2 and 3 both suffice.
   I assume that `PATH` for `conda`-related programs (`conda`, `activate`, etc.) are set properly.
2. Git clone the whole repository, say under `~/datasmart`.
3. In the root directory of the repository, run `./install_python_env.sh`
4. Set `PYTHONPATH` to include the root directory of the repository somehow, say in `.profile`.

Certainly, if you are an experienced Python user, you can replicate the above steps without `conda`.

## Usage

Before each time using DataSMART, run `. activate datasmart` to switch to the correct environment.

## Config location.

DataSMART will read the config files for modules and actions under three different locations, in order of precedence.

1. First, config files under the parent directory for invoked python script will be tried
   (more precisely, `sys.path[0]`).
2. Then, config files under `~/.datasmart` will be tried.
3. Last, default config files under the repository will be tried.

I think most of the time, it's most convenient to have all configuration files under `~/.datasmart`.