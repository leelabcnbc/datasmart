# DataSMART

[![Build Status](https://travis-ci.org/leelabcnbc/datasmart.svg?branch=master)](https://travis-ci.org/leelabcnbc/datasmart)
[![Coverage Status](https://coveralls.io/repos/github/leelabcnbc/datasmart/badge.svg?branch=master)](https://coveralls.io/github/leelabcnbc/datasmart?branch=master)
[![codecov.io](https://codecov.io/github/leelabcnbc/datasmart/coverage.svg?branch=master)](https://codecov.io/github/leelabcnbc/datasmart?branch=master)
[![Dependency Status](https://gemnasium.com/badges/github.com/leelabcnbc/datasmart.svg)](https://gemnasium.com/github.com/leelabcnbc/datasmart)
[![Code Climate](https://codeclimate.com/github/leelabcnbc/datasmart/badges/gpa.svg)](https://codeclimate.com/github/leelabcnbc/datasmart)
[![Issue Count](https://codeclimate.com/github/leelabcnbc/datasmart/badges/issue_count.svg)](https://codeclimate.com/github/leelabcnbc/datasmart)
[![Documentation Status](http://readthedocs.org/projects/datasmart/badge/?version=latest)](http://datasmart.readthedocs.org/en/latest/?badge=latest)

DataSMART is designed to manage data and processing pipelines in science labs. Click the docs badge above to learn about it.

This project is under heavy development...

## How to run demo

Make sure `conda` is installed before, and you have a running `mongod` at `127.0.0.1:27017`.

1. `git clone` the project, say, under `~/Research/datasmart`.
2. `cd ~/Research/datasmart`
3. `./install_python_env.sh`
4. `. activate datasmart`
5. `./install_config_core.py`
6. `./install_action.py ../datasmart-demo demo/school_grade_input`
7. change directory to `../datasmart-demo` and then

	 ~~~bash
	 . activate datasmart
	 export PYTHONPATH="${HOME}/Research/datasmart:$PYTHONPATH"
	 jupyter notebook
	 ~~~
8. run notebook `demo_school_grade_input.ipynb`
9. optionally, you can also try the manual interface, by running `./start_demo_school_grade_input.sh`
