export TWINE_USERNAME=nonlogicaldev
export PIP_VERSION=v$(shell poetry version -s)

.PHONY: version
version:
	@poetry version -s

.PHONY: version.tag
version.tag:
	git tag -f "$(PIP_VERSION)"
	git push origin -f "$(PIP_VERSION)"

.PHONY: version.bump-minor
version.bump-minor:
	poetry version minor

.PHONY: version.bump-patch
version.bump-patch:
	poetry version patch

.PHONY: deps
deps:
	poetry install

.PHONY: dist
dist:
	poetry build

.PHONY: dist.release.pypi
dist.release.pypi:
	poetry publish

.PHONY: dist.release.gh
dist.release.gh: dist
	-gh release delete $(PIP_VERSION)
	gh release create $(PIP_VERSION) ./dist/*

.PHONY: clean
clean:
	-rm -rf dist
