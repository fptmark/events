S2R_DIR = ~/Projects/schema2rest
GENERATOR_DIR = $(S2R_DIR)/generators
CONVERTER_DIR = $(S2R_DIR)/convert

.PHONY: clean code run cli

firsttime: setup schema code redis services
	brew install mongo
	brew install redis
	cp $(S2R_DIR)/config.json config.json

redis:
	brew install redis
	brew services start redis

services: $(S2R_DIR)/services/* schema.yaml
	rm -rf app/services
	mkdir -p app/services
	cp -r $(S2R_DIR)/services app
	python $(GENERATOR_DIR)/gen_service_routes.py schema.yaml .

all: schema code run 

schema: schema.yaml schema.png 

clean: 
	rm -rf app schema.yaml app.log schema.png

code:	schema main db models routes services
	mkdir -p app/utilities
	cp -r $(S2R_DIR)/config.py app/utilities

models: $(GENERATOR_DIR)/gen_models.py schema.yaml $(GENERATOR_DIR)/templates/models/*
	rm -rf app/models
	python $(GENERATOR_DIR)/gen_models.py schema.yaml .

routes: $(GENERATOR_DIR)/gen_routes.py schema.yaml $(GENERATOR_DIR)/templates/routes/*
	rm -rf app/routes
	python $(GENERATOR_DIR)/gen_routes.py schema.yaml .

main: $(GENERATOR_DIR)/gen_main.py schema.yaml $(GENERATOR_DIR)/templates/main/*
	rm -f app/main.py
	python $(GENERATOR_DIR)/gen_main.py schema.yaml .

db: $(GENERATOR_DIR)/gen_db.py schema.yaml $(GENERATOR_DIR)/templates/db/*
	rm -rf app/db.py
	python $(GENERATOR_DIR)/gen_db.py schema.yaml .

setup:	$(S2R_DIR)/requirements.txt
	pip install -r r$(S2R_DIR)/equirements.txt

schema.yaml : schema.mmd $(CONVERTER_DIR)/schemaConvert.py
	python $(CONVERTER_DIR)/schemaConvert.py schema.mmd .

schema.png: schema.mmd
	cat schema.mmd | sed '/[[:alnum:]].*%%/ s/%%.*//' | mmdc -i - -o schema.png

indexes:
	python $(GENERATOR_DIR)/update_indices.py schema.yaml

run:	
	PYTHONPATH=. python app/main.py

test: test.py
	pytest -s test.py

cli:
	PYTHONPATH=. python cli/cli.py


