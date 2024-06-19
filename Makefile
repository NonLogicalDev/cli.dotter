export TWINE_USERNAME=nonlogicaldev

.PHONY: version
version:
	@poetry version -s

.PHONY: version.tag
version.tag: TAG_VERSION=v$(shell poetry version -s)
version.tag:
	git tag "$(TAG_VERSION)"
	git push origin "$(TAG_VERSION)"

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
	poetry release

.PHONY: dist.release.gh
dist.release.gh: dist
	gh release create $(shell $(MAKE) version) ./dist

.PHONY: clean
clean:
	-rm -rf dist
