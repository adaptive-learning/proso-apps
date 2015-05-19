# PROSO Apps

[![Build Status](https://travis-ci.org/adaptive-learning/proso-apps.png)](https://travis-ci.org/adaptive-learning/proso-apps)

## Development

Setup your local virtual environment:

	mkvirtualenv proso-apps

If the environment already exists, activate it:

	workon proso-apps

To install/reinstall the project:

	make install|reinstall

If you want to build download javascript dependencies, you have to run Bower:

	make bower

To run tests:

	make test

## Release

In case of milestone:

	make MILESTONE=<milestone> release

In case of final version (you have to setup your PIP environment before):

	make release



