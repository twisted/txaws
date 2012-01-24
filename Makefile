version:
	@python -c "from txaws import version;print version.txaws;"


clean:
	find ./ -name "*~" -exec rm {} \;
	find ./ -name "*.pyc" -exec rm {} \;
	find ./ -name "*.pyo" -exec rm {} \;
	find . -name "*.sw[op]" -exec rm {} \;
	rm -rf _trial_temp/ build/ dist/ MANIFEST *.egg-info


build:
	@python setup.py build
	@python setup.py sdist


virtual-dir-setup: VERSION ?= 2.5
virtual-dir-setup:
	-@test -d .venv-$(VERSION) || virtualenv -p Python$(VERSION) .venv-$(VERSION)
	-@test -e .venv-$(VERSION)/bin/twistd || . .venv-$(VERSION)/bin/activate && pip install twisted
	-@test -e .venv-$(VERSION)/bin/pep8 || . .venv-$(VERSION)/bin/activate && pip install pep8
	-@test -e .venv-$(VERSION)/bin/pyflakes || . .venv-$(VERSION)/bin/activate && pip install pyflakes
	-. .venv-$(VERSION)/bin/activate && pip install lxml
	-. .venv-$(VERSION)/bin/activate && pip install PyOpenSSL
	-. .venv-$(VERSION)/bin/activate && pip install venusian
	-. .venv-$(VERSION)/bin/activate && pip install http://labix.org/download/python-dateutil/python-dateutil-1.5.tar.gz


virtual-dir-remove: VERSION ?= 2.5
virtual-dir-remove:
	rm -rfv .venv-$(VERSION)


virtual-builds:
	-@test -e "`which python2.5`" && VERSION=2.5 make virtual-dir-setup || echo "Couldn't find Python2.5"
	-@test -e "`which python2.6`" && VERSION=2.6 make virtual-dir-setup || echo "Couldn't find Python2.6"
	-@test -e "`which python2.7`" && VERSION=2.7 make virtual-dir-setup || echo "Couldn't find Python2.7"


virtual-check: VERSION ?= 2.5
virtual-check:
	-. .venv-$(VERSION)/bin/activate && trial ./txaws
	-. .venv-$(VERSION)/bin/activate && pep8 ./txaws
	-. .venv-$(VERSION)/bin/activate && pyflakes ./txaws


virtual-checks: virtual-builds
	-@test -e "`which python2.5`" && VERSION=2.5 make virtual-check
	-@test -e "`which python2.6`" && VERSION=2.6 make virtual-check
	-@test -e "`which python2.7`" && VERSION=2.7 make virtual-check


clean-virtual-builds: clean
	@VERSION=2.5 make virtual-dir-remove
	@VERSION=2.6 make virtual-dir-remove
	@VERSION=2.7 make virtual-dir-remove


virtual-build-clean: clean-virt build virtual-build
.PHONY: virtual-build-clean


check: MOD ?= txaws
check: build sdist
	trial ./txaws


build-docs:
	cd docs/sphinx; make html


register:
	python setup.py register


upload: check
	python setup.py sdist upload --show-response


upload-docs: build-docs
	python setup.py upload_docs --upload-dir=docs/html/
