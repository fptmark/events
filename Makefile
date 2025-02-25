S2R_DIR = ~/Projects/schema2rest
GENERATORS = $(S2R_DIR)

.PHONY: clean code

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
	python $(GENERATORS)/gen_service_routes.py schema.yaml .

all: schema code run 

schema: schema.yaml schema.png 

clean: 
	rm -rf app schema.yaml app.log schema.png

code:	schema main db models routes services
	mkdir -p app/utilities
	cp -r $(S2R_DIR)/config.py app/utilities

models: $(GENERATORS)/gen_models.py schema.yaml $(GENERATORS)/templates/models/*
	rm -rf app/models
	python $(GENERATORS)/gen_models.py schema.yaml .

routes: $(GENERATORS)/gen_routes.py schema.yaml $(GENERATORS)/templates/routes/*
	rm -rf app/routes
	python $(GENERATORS)/gen_routes.py schema.yaml .

main: $(GENERATORS)/gen_main.py schema.yaml $(GENERATORS)/templates/main/*
	rm -f app/main.py
	python $(GENERATORS)/gen_main.py schema.yaml .

db: $(GENERATORS)/gen_db.py schema.yaml $(GENERATORS)/templates/db/*
	rm -rf app/db.py
	python $(GENERATORS)/gen_db.py schema.yaml .

setup:	$(S2R_DIR)/requirements.txt
	pip install -r r$(S2R_DIR)/equirements.txt

schema.yaml : schema.mmd $(GENERATORS)/schemaConvert.py
	python $(GENERATORS)/schemaConvert.py schema.mmd .
	python $(S2R_DIR)/update_indicies.py schema.yaml

schema.png: schema.mmd
	cat schema.mmd | sed '/[[:alnum:]].*%%/ s/%%.*//' | mmdc -i - -o schema.png

run: app/main.py
	PYTHONPATH=. python app/main.py

test: test.py
	pytest -s test.py
