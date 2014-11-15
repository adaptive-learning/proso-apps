#!/bin/bash
SELF=$0
WORKSPACE_DIR=`dirname $SELF`
WORK_TREE=$WORKSPACE_DIR
APP_DIR=$WORKSPACE_DIR
if [ "$GEOGRAPHY_DATA_DIR" ]; then
	DATA_DIR="$GEOGRAPHY_DATA_DIR"
else
	DATA_DIR="$APP_DIR"
fi
GIT_DIR=$WORK_TREE/.git
GIT_COMMAND="git --git-dir=$GIT_DIR --work-tree=$WORK_TREE"

###############################################################################
# install requirements
###############################################################################


	echo " * python $APP_DIR/setup.py install"
  cd $WORKSPACE_DIR

  python $APP_DIR/setup.py install

###############################################################################
# reset the application
###############################################################################

  cd $WORKSPACE_DIR/proso_questions_client

	echo " * npm install"
    npm install
	echo " * grunt deploy"
	grunt deploy

  echo "rm -rf $APP_DIR/../data_repo"
  rm -rf $APP_DIR/../data_repo

	echo "./manage.py load_img"
	$APP_DIR/manage.py load_img $APP_DIR/../data_repo/img

	echo " * collect static | tail"
	$APP_DIR/manage.py collectstatic --noinput | tail
	echo "HASHES = $( python $APP_DIR/manage.py static_hashes )" > $APP_DIR/hashes.py

	echo " * remove django cache"
	rm -rf $DATA_DIR/.django_cache

	echo "./manage.py syncdb"
	$APP_DIR/manage.py syncdb 

	echo "./manage.py migrate"
	$APP_DIR/manage.py migrate 

  echo "git clone $PROSO_DATA_REPO $APP_DIR/../data_repo"
  git clone $PROSO_DATA_REPO $APP_DIR/../data_repo

	echo "./manage.py load_texts"
	$APP_DIR/manage.py load_texts $APP_DIR/../data_repo/texts.json

	echo "./manage.py load_questions"
	$APP_DIR/manage.py load_questions $APP_DIR/../data_repo/questions.json

	echo "cp local_settings.py"
	cp $APP_DIR/../data_repo/local_settings.py $APP_DIR/production/
