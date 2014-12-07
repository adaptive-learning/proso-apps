TEST_DIR=$(CURDIR)/test
RESOURCES_DIR=$(CURDIR)/resources

PEP8=pep8 --ignore=E501,E225,E123,E128
APPS=proso_common proso_flashcards proso_models proso_questions proso_questions_client
GRUNT_APPS=proso_questions_client



################################################################################

upload: grunt test register
	python setup.py sdist upload

register:
	python setup.py register


################################################################################

test: reinstall
	python -m unittest discover -p test_*.py -s proso
	for APP in $(APPS); do \
		python manage.py test ${APP} --traceback; \
	done;

reinstall: check uninstall install

develop: check
	python setup.py develop

install: check
	python setup.py sdist
	pip install dist/proso-apps-*

uninstall:
	pip uninstall --yes proso-apps

check:
	flake8 --ignore=E501,E225,E123,E128 --exclude=*/migrations/*.py proso_models $(APPS)

grunt:
	for APP in $(GRUNT_APPS); do \
		cd $${APP}; \
		npm install; \
		grunt deploy; \
		cd -; \
	done;
