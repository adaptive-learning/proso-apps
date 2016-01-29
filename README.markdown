# PROSO Apps

[![Build Status](https://travis-ci.org/adaptive-learning/proso-apps.png)](https://travis-ci.org/adaptive-learning/proso-apps)

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


## Migration to python3

### social-auth

details at http://psa.matiasaguirre.net/docs/configuration/porting_from_dsa.html

 - replace'social_auth' with 'social.apps.django_app.default' in INSTALLED_APPS in settings.py
 - replace old include with 'url('', include('social.apps.django_app.urls', namespace='social'))' in urls.py
 - change setting vars names to connect to google and facebook in setting.py
 - change facebook and google backends in AUTHENTICATION_BACKENDS  in settings.py
 - in google developer console allow Google+ API
 - clean the session and force the users to login again in your site or run script to update session in DB
  

