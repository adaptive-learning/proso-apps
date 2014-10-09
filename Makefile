TEST_DIR=$(CURDIR)/test
RESOURCES_DIR=$(CURDIR)/resources

PEP8=pep8 --ignore=E501,E225,E123,E128

################################################################################


upload: test register
	python setup.py sdist upload

register:
	python setup.py register

################################################################################


test: reinstall
	python manage.py test proso_common --traceback
	python manage.py test proso_models --traceback
	python manage.py test proso_questions --traceback

reinstall: check uninstall install

develop: check
	python setup.py develop

install:check
	python setup.py sdist
	pip install dist/proso-apps-*

uninstall:
	pip uninstall --yes proso-apps

check:
	${PEP8} proso_models proso_questions proso_ab proso
	pyflakes proso_models proso_questions proso_ab proso

