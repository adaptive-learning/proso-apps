[![Stories in Ready](https://badge.waffle.io/adaptive-learning/proso-apps.png?label=ready&title=Ready)](https://waffle.io/adaptive-learning/proso-apps)
[![Stories in Ready](https://badge.waffle.io/adaptive-learning/proso-apps.png?label=ready&title=Ready)](https://waffle.io/adaptive-learning/proso-apps)
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

You have to setup you PIP environment. Create a `~/.pypirc` file containing your credentials to
[https://pypi.python.org](https://pypi.python.org):

```
[server-login]
username: ...
password: ...
```

Make sure you have the environment active, or activate it:

	workon proso-apps
	
Major version is release manually.

In case of final minor version (you have to be in `master` branch):

	make release

In case of final micro version (you have to be in proper `master-*.X` branch):

	make release-micro
