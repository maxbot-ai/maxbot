-include .env

POETRY_VERSION_MAIN=$(shell poetry version -s 2>/dev/null)
POETRY_VERSION_DATE=$(shell date "+%Y%m%d%H%M%S")

ifeq ($(MIDVIX_ENV), dev)
	PYPI_REPO=testpypi
	POETRY_VERSION_NAME=a.dev
endif

ifeq ($(MIDVIX_ENV), test)
	PYPI_REPO=testpypi
	POETRY_VERSION_NAME=b.dev
endif

ifeq ($(MIDVIX_ENV), prod)
	PYPI_REPO=pypi
    POETRY_VERSION_NAME=b2
    POETRY_VERSION_DATE=
endif

$(eval POETRY_VERSION_CUR=$(shell poetry version -s))
$(eval POETRY_VERSION_NEW=$(POETRY_VERSION_MAIN)$(POETRY_VERSION_NAME)$(POETRY_VERSION_DATE))

.PHONY: test

test:
	pytest -p no:maxbot_stories --cov=maxbot --cov-report html --cov-fail-under=95

stories:
	pytest --bot examples/hello-world examples/hello-world/stories.yaml
	pytest --bot examples/echo examples/echo/stories.yaml
	pytest --bot examples/restaurant examples/restaurant/stories.yaml
	pytest --bot examples/reservation-basic examples/reservation-basic/stories.yaml
	pytest --bot examples/reservation examples/reservation/stories.yaml
	pytest --bot examples/digression-showcase examples/digression-showcase/stories.yaml
	pytest --bot examples/rpc-showcase examples/rpc-showcase/stories.yaml

clean:
	rm -f dist/maxbot-*.*.*-py3-none-any.whl
	rm -f dist/maxbot-*.*.*.tar.gz

version_bumb:
	poetry version $(POETRY_VERSION_NEW)

version_revert:
	poetry version $(POETRY_VERSION_CUR)

wheel:
	poetry build --format wheel

tag:
	git tag "v.$(POETRY_VERSION_NEW)"
	git push origin "v.$(POETRY_VERSION_NEW)"

publish:
	poetry publish -r $(PYPI_REPO)

build_wheel: clean version_bumb wheel tag

build_docs:
	rm -rf website/build
	cd website;npm install;npm run build;cd ..;

publish_docs:
	rsync --delete -rltH --exclude='.git*' ./website/build/* $(WEB_SITE_SRV):$(WEB_SITE_PATH_PREFIX)-$(MIDVIX_ENV)/$(WEB_SITE_PROJECT)

dep_docs: build_docs publish_docs

dep_internal: build_wheel dep_docs version_revert

dep: build_wheel publish dep_docs version_revert
