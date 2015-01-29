TEST_DIR=$(CURDIR)/test
RESOURCES_DIR=$(CURDIR)/resources

PEP8=pep8 --ignore=E501,E225,E123,E128
APPS=proso_common proso_flashcards proso_models proso_questions proso_questions_client
GRUNT_APPS=proso_questions_client

VERSION:=$(shell grep "VERSION = '.*'" proso/release.py | awk -F ' = ' '{print $$2}' | tr -d "'")
MAJOR_VERSION=$(word 1,$(subst ., ,$(VERSION)))
MINOR_VERSION=$(word 2,$(subst ., ,$(VERSION)))
MICRO_VERSION=$(word 3,$(subst ., ,$(VERSION)))


################################################################################

upload: grunt test register
	python setup.py sdist upload

register:
	python setup.py register


################################################################################

test: reinstall
	python -m unittest discover -p test_*.py -s proso
	for APP in $(APPS); do \
		python manage.py test $$APP --traceback; \
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


################################################################################

publish-version:
	git reset
	git add proso/release.py
	git commit -m 'release a new version $(VERSION)'
	git tag release-$(VERSION)

increase-major:
	MAJOR=`expr $(MAJOR_VERSION) + 1`; \
	MINOR=0; \
	MICRO=0; \
	sed -i "s/VERSION = '.*'/VERSION = '$${MAJOR}.$${MINOR}.$${MICRO}'/g" proso/release.py; \
	$(MAKE) publish-version

increase-minor:
	MAJOR=$(MAJOR_VERSION); \
	MINOR=`expr $(MINOR_VERSION) + 1`; \
	MICRO=0; \
	sed -i "s/VERSION = '.*'/VERSION = '$${MAJOR}.$${MINOR}.$${MICRO}'/g" proso/release.py;
	$(MAKE) publish-version

increase-micro:
	MAJOR=$(MAJOR_VERSION); \
	MINOR=$(MINOR_VERSION); \
	MICRO=`expr $(MICRO_VERSION) + 1`; \
	sed -i "s/VERSION = '.*'/VERSION = '$${MAJOR}.$${MINOR}.$${MICRO}'/g" proso/release.py;
	$(MAKE) publish-version
