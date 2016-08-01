# PROSO Apps

[![Build Status](https://travis-ci.org/adaptive-learning/proso-apps.png)](https://travis-ci.org/adaptive-learning/proso-apps)
[![Documentation Status](https://readthedocs.org/projects/proso-apps/badge/?version=latest)](http://proso-apps.readthedocs.org/en/latest/)

## Development

Setup your local virtual environment:

	mkvirtualenv proso-apps

If the environment already exists, activate it:

	workon proso-apps

To install/reinstall the project:

	make install|reinstall

If you want to download javascript dependencies, you have to run Bower and grunt:

	make build-js

If you want to download javascript dependencies and create a symbolic link to clone of proso-apps-js repository, you have to run Bower (develop) and grunt:

	make build-js-develop

To run tests:

	make test

## Release

In case of final major version (you have to setup your PIP environment before):

	make release

In case of final micro version:

	make release-micro
