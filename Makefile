S2R_DIR = ~/Projects/schema2rest
GENERATORS = $(S2R_DIR)/generators

.PHONY: clean code

firsttime: setup schema code 
	cp $(S2R_DIR)/config.json config.json

all: schema code test 

schema: schema.yaml schema.png

clean: 
	rm -rf app schema.yaml app.log schema.png

code:	schema main db models routes
	cp -r $(S2R_DIR)/utilities app

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

schema.yaml: schema.mmd $(GENERATORS)/schemaConvert.py
	python $(GENERATORS)/schemaConvert.py schema.mmd .

schema.png: schema.mmd
	mmdc -i schema.mmd -o schema.png

test: app/main.py
	PYTHONPATH=. python app/main.py
