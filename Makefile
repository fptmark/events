S2R_DIR = ~/Projects/schema2rest
GENERATOR_DIR = $(S2R_DIR)/generators
CONVERTER_DIR = $(S2R_DIR)/convert

BACKEND ?= mongo

.PHONY: clean code run cli

install: setup rebuild

rebuild: 
	rm -rf $(BACKEND)
	echo "Using existing config.json"
	mkdir -p $(BACKEND)/app
	cp $(S2R_DIR)/src/utilities/utils.py $(BACKEND)/app
	mkdir -p $(BACKEND)/app/services/auth
	cp $(S2R_DIR)/src/services/auth/cookies/*.py $(BACKEND)/app/services
	python $(S2R_DIR)/generate_code.py schema.mmd mongo mongo

redis:
	brew services start redis

services: $(S2R_DIR)/services/* schema.yaml
	rm -rf app/services
	mkdir -p app/services
	cp -r $(S2R_DIR)/services app
	python $(GENERATOR_DIR)/gen_service_routes.py schema.yaml .

all: schema code run 

schema: schema.yaml 

clean: 
	rm -rf app schema.yaml app.log schema.png
	mkdir app

code:	schema.yaml 
	mkdir -p $(BACKEND)/app/utilities
	cp -r $(S2R_DIR)/utils.py app/utilities
	python -m generators.gen_main schema.yaml . $(BACKEND)
	python -m generators.gen_db schema.yaml ./$(BACKEND) $(BACKEND)
	python -m generators.gen_models schema.yaml ./$(BACKEND) $(BACKEND)
	python -m generators.gen_routes schema.yaml ./$(BACKEND) $(BACKEND)
	python -m generators.gen_service_routes schema.yaml ./$(BACKEND) $(BACKEND)

setup:	$(S2R_DIR)/requirements.txt
	pip install -r r$(S2R_DIR)/requirements.txt
	brew install mongo
	brew install redis

schema.yaml : schema.mmd 
	python -m converter.schemaConvert schema.mmd .
	cat schema.mmd | sed '/[[:alnum:]].*%%/ s/%%.*//' | mmdc -i - -o schema.png

indexes:
	python $(GENERATOR_DIR)/update_indices.py schema.yaml

run:	
	PYTHONPATH=. python app/main.py

test: test.py
	pytest -s test.py

cli:
	PYTHONPATH=. python cli/cli.py


