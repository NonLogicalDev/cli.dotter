export TWINE_USERNAME=nonlogicaldev
export VERSION=$(shell pipenv run python -c 'exec(open("dotter/version.py").read()); print(__version__)')

.PHONY: install
install:
	pip install -e .

.PHONY: deps
deps:
	pipenv sync

.PHONY: dist
dist:
	pipenv run python3 setup.py sdist

.PHONY: clean
clean:
	-rm -rf build
	-rm -rf dist
	-rm -rf *.egg-info

pip.tag:
	git tag $(VERSION)

pip.release: clean dist
	pipenv run twine upload --repository testpypi dist/*

pip.release.prod: clean dist
	pipenv run twine upload dist/*
