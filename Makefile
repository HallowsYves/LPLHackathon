# Used by `sam build` (infra/template.yaml, BuildMethod: makefile): package only what the Lambda needs.
build-ApiFunction:
	mkdir -p "$(ARTIFACTS_DIR)/data"
	cp -R backend "$(ARTIFACTS_DIR)/backend"
	cp -R data/ground_truth "$(ARTIFACTS_DIR)/data/ground_truth"
	find "$(ARTIFACTS_DIR)" -name __pycache__ -type d -prune -exec rm -rf {} +
