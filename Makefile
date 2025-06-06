S2R_DIR = ~/Projects/schema2rest
GENERATOR_DIR = $(S2R_DIR)/generators
CONVERTER_DIR = $(S2R_DIR)/convert
PYPATH = PYTHONPATH=~/Projects/schema2rest

BACKEND ?= mongo

.PHONY: clean code run cli

install: setup firsttime rebuild

firsttime: 
	rm -rf app
	echo "Using existing config.json"
	mkdir -p app
	cp $(S2R_DIR)/src/utilities/utils.py app
	mkdir -p app/services/auth
	cp $(S2R_DIR)/src/services/auth/cookies/*.py app/services

rebuild:
	$(PYPATH) python $(S2R_DIR)/src/generate_code.py schema.mmd . Events $(BACKEND) 

models:
	$(PYPATH) python -m generators.models.gen_model_main schema.yaml . $(BACKEND)

redis:
	brew services start redis

services: $(S2R_DIR)/services/* schema.yaml
	rm -rf app/services
	mkdir -p app/services
	cp -r $(S2R_DIR)/services app
	$(PYPATH) python $(GENERATOR_DIR)/gen_service_routes.py schema.yaml .

all: schema code run 

schema: schema.yaml 

clean: 
	rm -rf app schema.yaml app.log schema.png

code:	schema.yaml 
	mkdir -p app/utilities
	cp -r $(S2R_DIR)/src/utilities/utils.py app/utilities
	$(PYPATH) python -m generators.gen_main schema.yaml . $(BACKEND)
	$(PYPATH) python -m generators.gen_db schema.yaml . $(BACKEND)
	$(PYPATH) python -m generators.gen_models schema.yaml . $(BACKEND)
	$(PYPATH) python -m generators.gen_routes schema.yaml . $(BACKEND)
	$(PYPATH) python -m generators.gen_service_routes schema.yaml . $(BACKEND)

setup:	$(S2R_DIR)/requirements.txt
	pip install -r r$(S2R_DIR)/requirements.txt
	brew install mongo
	brew install redis

schema.yaml : schema.mmd 
	$(PYPATH) python -m convert.schemaConvert schema.mmd 
	cat schema.mmd | sed '/[[:alnum:]].*%%/ s/%%.*//' | mmdc -i - -o schema.png

indexes:
	python $(GENERATOR_DIR)/update_indices.py schema.yaml

run:	
	PYTHONPATH=. python app/main.py $(BACKEND).json --db-type elasticsearch

test: test.py
	pytest -s test.py

cli:
	PYTHONPATH=. python cli/cli.py

runes:
	docker run -d --name es \
	  -p 9200:9200 -p 9300:9300 \
	  -e discovery.type=single-node \
	  -e xpack.security.enabled=false \
	  elasticsearch:8.12.2
