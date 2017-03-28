TEST_DIR=$(CURDIR)/test
RESOURCES_DIR=$(CURDIR)/resources

PEP8=pep8 --ignore=E501,E225,E123,E128

VERSION_FULL:=$(shell grep "VERSION = '.*'" proso/release.py | awk -F ' = ' '{print $$2}' | tr -d "'")
VERSION:=$(shell echo $(VERSION_FULL) | awk -F '-' '{print $$1}')
VERSION_SUFFIX:=$(shell echo $(VERSION_FULL) | awk -F '-' '{print $$2}')
MAJOR_VERSION=$(word 1,$(subst ., ,$(VERSION)))
MINOR_VERSION=$(word 2,$(subst ., ,$(VERSION)))
MICRO_VERSION=$(word 3,$(subst ., ,$(VERSION)))


################################################################################

upload: reinstall grunt register
	python setup.py sdist upload

register:
	python setup.py register


################################################################################

docker-pull:
	docker-compose pull

docker-up: docker-pull
	docker-compose up

docker-bash: docker-pull
	docker-compose run --rm proso-apps bash

docker-tests: docker-pull
	docker-compose run --rm proso-apps bash -c "cd /proso-apps && make test"

sphinx-apidoc:
	sphinx-apidoc -o docs/ref . `find . -name test_*.py -or -name *test.py -or -name migrations -or -name management -or -name setup.py -or -name testproject -or -name manage.py`

doctest:
	cd docs; $(MAKE) doctest

unittest:
	python -m unittest discover -p test_*.py -s proso;

django-test:
	python manage.py test --traceback --pattern *_test.py;

test: unittest django-test

reinstall: check uninstall install

develop-js:
	rm -rf testproject/bower_components/proso-apps-js; \
	ln -s ../../../proso-apps-js/dist testproject/bower_components/proso-apps-js;

develop: check
	python setup.py develop

bower:
	cd testproject; bower install -f

bower-develop: bower develop-js

grunt:
	cd testproject; grunt

build-js: bower grunt

build-js-develop: bower-develop grunt

install: check
	python setup.py sdist
	pip install dist/proso-apps-$(VERSION_FULL)*

uninstall:
	pip uninstall --yes proso-apps

check:
	pip install flake8
	flake8 --ignore=E501,E225,E123,E128,W503,E731 --exclude=*/migrations/*.py,*/static/bower_components,setup.py,docs/conf.py,.ropeproject .


################################################################################

release-micro:
	$(MAKE) milestone; \
	$(MAKE) upload; \
	$(MAKE) increase-micro; \
	$(MAKE) snapshot; \
	git add proso/release.py; \
	$(MAKE) commit-start-working; \
	git push;

release:
	$(MAKE) milestone; \
	$(MAKE) upload; \
	$(MAKE) create-minor-branch; \
	git checkout master; \
	$(MAKE) increase-minor; \
	$(MAKE) snapshot; \
	git add proso/release.py; \
	$(MAKE) commit-start-working; \
	git push;

milestone:
	MAJOR=$(MAJOR_VERSION); \
	MINOR=$(MINOR_VERSION); \
	MICRO=$(MICRO_VERSION); \
	sed -i "s/VERSION = '.*'/VERSION = '$${MAJOR}.$${MINOR}.$${MICRO}'/g" proso/release.py; \
	$(MAKE) publish-version; \

create-minor-branch:
	MAJOR=$(MAJOR_VERSION); \
	MINOR=$(MINOR_VERSION); \
	git checkout -b master-$${MAJOR}.$${MINOR}.X; \
	$(MAKE) increase-micro; \
	$(MAKE) snapshot; \
	git add proso/release.py; \
	$(MAKE) commit-start-working; \
	git push origin master-$${MAJOR}.$${MINOR}.X

commit-back-to-snapshot:
	git commit -m 'back to $(VERSION_FULL)'; \

commit-start-working:
		git commit -m 'start working on $(VERSION)'; \

snapshot:
	MAJOR=$(MAJOR_VERSION); \
	MINOR=$(MINOR_VERSION); \
	MICRO=$(MICRO_VERSION); \
	sed -i "s/VERSION = '.*'/VERSION = '$${MAJOR}.$${MINOR}.$${MICRO}.dev'/g" proso/release.py; \

publish-version:
	git reset
	git add proso/release.py
	git commit -m 'release a new version $(VERSION_FULL)'
	git tag release-$(VERSION_FULL)
	git push origin release-$(VERSION_FULL)

increase-major:
	MAJOR=`expr $(MAJOR_VERSION) + 1`; \
	MINOR=0; \
	MICRO=0; \
	sed -i "s/VERSION = '.*'/VERSION = '$${MAJOR}.$${MINOR}.$${MICRO}'/g" proso/release.py; \

increase-minor:
	MAJOR=$(MAJOR_VERSION); \
	MINOR=`expr $(MINOR_VERSION) + 1`; \
	MICRO=0; \
	sed -i "s/VERSION = '.*'/VERSION = '$${MAJOR}.$${MINOR}.$${MICRO}'/g" proso/release.py;

increase-micro:
	MAJOR=$(MAJOR_VERSION); \
	MINOR=$(MINOR_VERSION); \
	MICRO=`expr $(MICRO_VERSION) + 1`; \
	sed -i "s/VERSION = '.*'/VERSION = '$${MAJOR}.$${MINOR}.$${MICRO}'/g" proso/release.py;
