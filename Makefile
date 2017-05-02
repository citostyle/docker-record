VENV_DIR = .venv
VENV_RUN = . $(VENV_DIR)/bin/activate

usage:             ## Show this help
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

install:           ## Install dependencies
	(test `which virtualenv` || pip install --user virtualenv || sudo pip install virtualenv)
	(test -e $(VENV_DIR) || virtualenv $(VENV_DIR))
	($(VENV_RUN) && pip install --upgrade pip)
	(test ! -e requirements.txt || ($(VENV_RUN) && pip install -r requirements.txt))

run:               ## Run main application
	($(VENV_RUN); bin/docker-record $(CONTAINER))

publish:           ## Publish the library to the central PyPi repository
	# build and upload archive
	($(VENV_RUN) && ./setup.py sdist upload)

test:              ## Run automated tests
	make lint && \
		$(VENV_RUN); DEBUG=$(DEBUG) PYTHONPATH=`pwd` nosetests --with-coverage --logging-level=WARNING --nocapture --no-skip --exe --cover-erase --cover-tests --cover-inclusive --cover-package=docker_record --with-xunit --exclude='$(VENV_DIR).*' .

lint:              ## Run code linter to check code style
	($(VENV_RUN); pep8 --max-line-length=100 --exclude=$(VENV_DIR),dist .)

clean:             ## Clean up
	rm -rf dist

.PHONY: usage clean install publish
