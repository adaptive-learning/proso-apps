#################
Development Guide
#################

*******************************
Optional fast start with docker
*******************************

Docker-compose installation
===========================
In case of Ubuntu 14.04::
    sudo apt-get update
    sudo apt-get install apt-transport-https ca-certificates apparmor
    sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
    echo 'deb https://apt.dockerproject.org/repo ubuntu-trusty main' | sudo tee /etc/apt/sources.list.d/docker.list
    sudo apt-get update
    sudo apt-get install -y docker-engine
    sudo bash -c "curl -L https://github.com/docker/compose/releases/download/1.6.2/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose"
    sudo chmod +x /usr/local/bin/docker-compose

More detailed info available at `Docker page <https://docs.docker.com/compose/install/>`_.

Available make commands (requires sudo)
=======================================
``docker-up`` -> run local development server at localhost:8000
``docker-tests`` -> run all tests in docker environment
``docker-bash`` -> attach to docker environment command line

********
Starting
********

System dependencies
===================

In case of Ubuntu::

  sudo apt-get install python-dev libpq-dev libfreetype6-dev libblas-dev liblapack-dev gfortran postgresql postgresql-contrib libpng-dev

In case of Fedora::

  sudo yum install python-devel freetype-devel libblas-devel lapack-devel gcc-fortran postgresql-server postgresql-contrib postgresql-devel postgresql-libs


PIP and Virtual Environment
===========================

You need to have `PIP <https://pypi.python.org/pypi/pip>`_ installed. Now, we try to install `virtualenvwrapper <http://virtualenvwrapper.readthedocs.org/en/latest/>`_::

  sudo pip install virtualenvwrapper

and add the following to your ``~/.bashrc`` file::

  export WORKON_HOME=$HOME/.virtualenvs
  source /usr/local/bin/virtualenvwrapper.sh

Using ``whereis python`` find your installation of Python 3.x. We will reference it as ``PYTHON_PATH``. Now, crate a virtual environment::

  mkvirtualenv -p $PYTHON_PATH proso-apps

If you want to use the environment in the future, just type::

  workon proso-apps

PostgreSQL
==========

Create a development user and database on your localhost::

  sudo -i -u postgres
  psql

You are in PostgreSQL shell. Execute::

  CREATE DATABASE proso_apps;
  CREATE USER proso_apps WITH PASSWORD 'proso_apps';
  GRANT ALL PRIVILEGES ON DATABASE "proso_apps" to proso_apps;

GIT repository
==============

Firstly, you need to clone our GIT repository::

  git clone git@github.com:adaptive-learning/proso-apps.git

or in case, you have no access::

  git clone https://github.com/adaptive-learning/proso-apps.git

Since now, we will work inside the cloned repository::

  cd proso-apps

After you clone the repository, install ``proso-apps``::

  make install

After successful installation, migrate database::

  ./manage.py migrate

Finally, we can run the test server::

  ./manage.py runserver


Sample database
===============

You can download a dump from PostgreSQL used by `www.slepemapy.cz <http://www.slepemapy.cz>`_ from
`data-private.slepemapy.cz/dump <http://data-private.slepemapy.cz/dump>`_ (the file is referenced as ``DUMP_FILE``) and
load it to your database::

  export PGPASSWORD=proso_apps
  psql -Uproso_apps --set ON_ERROR_STOP=on proso_apps < $DUMP_FILE

If you want to create a new dump file, just run::

  export PGPASSWORD=...
  pg_dump -h db.fi.muni.cz -Uweb_slepemapy -nweb_slepemapy_prod --exclude-table=proso_models_audit "dbname=pgdb sslmode=require" > $DUMP_FILE

