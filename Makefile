TEST_DIR=$(CURDIR)/test
RESOURCES_DIR=$(CURDIR)/resources

PEP8=pep8 --ignore=E501,E225,E123,E128

################################################################################


upload: grunt test register
	python setup.py sdist upload

register:
	python setup.py register

################################################################################


test: reinstall
	python -m unittest discover -p test_*.py -s proso
	python manage.py test proso_common --traceback
	python manage.py test proso_models --traceback
	python manage.py test proso_questions --traceback
	python manage.py test proso_questions --traceback

reinstall: check uninstall install

develop: check
	python setup.py develop

install: check
	python setup.py sdist
	pip install dist/proso-apps-*

uninstall:
	pip uninstall --yes proso-apps

check:
	flake8 --ignore=E501,E225,E123,E128 --exclude=*/migrations/*.py proso_models proso_questions proso_ab proso

grunt:
	cd proso_questions_client; \
	npm install; \
	grunt deploy;
