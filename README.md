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

Certainly, if you are an experienced Python user, you can replicate the above steps without `conda`.

## Install configurations

The scripts mentioned in this section requires Python 3.5+ to run (not necessarily the python in `datasmart` conda environment).

In the repository directory, run `./install_config_core.py` to install core configurations. Usually, the configuration for `filetransfer` and `db` should be modified.

Then, for individual actions, run `./install_action.py` to install them into separate folders. By install, I mean copying a set of configurations for those actions.

For example, to install CORTEX related actions into `~/Documents/datasmart-cortex`, run `./install_action.py ~/Documents/datasmart-cortex leelab/cortex_exp leelab/cortex_exp_sorted`

The syntax for `install_action.py` is `install_action.py [DIRECTORY] [action1] [action2] ...`

After installing, please go to the `config` subdirectory to modify the default configurations as needed. 

In that directory, run `start_*` scripts to start the action.

## Usage

Before each time using DataSMART, run `. activate datasmart` to switch to the correct environment.

## Config location.

DataSMART will read the config files for modules and actions under three different locations, in order of precedence.

1. First, config files under the parent directory for invoked python script will be tried
   (more precisely, `sys.path[0]`).
2. Then, config files under `~/.datasmart` will be tried.
3. Last, default config files under the repository will be tried.

I think most of the time, it's most convenient to have all configuration files under `~/.datasmart`.