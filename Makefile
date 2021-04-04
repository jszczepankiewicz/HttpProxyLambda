check: ## Run linters
	@echo '*** running checks ***'
	flake8
	yamllint -f parsable .
	cfn-lint -f parseable
	@echo '*** all checks passing ***'

test: check ## Run tests
	@echo '*** running tests ***'
	PYTHONPATH=./src pytest --cov=src --cov-branch --cov-report term-missing
	@echo '*** all tests passing ***'
