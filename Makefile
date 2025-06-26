S2R_DIR = ~/Projects/schema2rest
GENERICS = $(S2R_DIR)/src/server_generic_files
GENERATOR_DIR = $(S2R_DIR)/generators
CONVERTER_DIR = $(S2R_DIR)/convert
PYPATH = PYTHONPATH=~/Projects/schema2rest
BACKEND ?= es
PROJECT_NAME ?= "Project Name Here"

.PHONY: clean code cli

install: setup clean rebuild

clean:	new schema rebuild

new: 
	rm -rf app
	cp -r $(GENERICS) app
	mv app/config/*.json .

rebuild:
	$(PYPATH) python $(S2R_DIR)/src/generate_code.py schema.mmd $(GENERICS) . 

main:
	$(PYPATH) python -m generators.gen_main schema.yaml . 

models:
	$(PYPATH) python -m generators.models.gen_model_main schema.yaml . 

redis:
	brew services start redis

services: 
	$(PYPATH) python -m generators.gen_service_routes schema.yaml $(GENERICS) .

all: schema code 

schema: schema.yaml 

code:	schema.yaml 
	mkdir -p app/utilities
	$(PYPATH) python -m generators.gen_main schema.yaml . 
	$(PYPATH) python -m generators.gen_models schema.yaml . 
	$(PYPATH) python -m generators.gen_service_routes schema.yaml $(GENERICS) . 

setup:	$(S2R_DIR)/requirements.txt
	pip install -r r$(S2R_DIR)/requirements.txt
	brew install mongo
	brew install redis

schema.yaml : schema.mmd 
	$(PYPATH) python -m convert.schemaConvert schema.mmd 
	cat schema.mmd | sed '/[[:alnum:]].*%%/ s/%%.*//' | mmdc -i - -o schema.png

indexes:
	PYTHONPATH=. python app/main.py $(BACKEND).json --initdb

run:	
	PYTHONPATH=. python app/main.py $(BACKEND).json 

runmongo:	
	PYTHONPATH=. python app/main.py mongo.json 

test: test.py
	pytest -s test.py

cli:
	PYTHONPATH=. python cli/cli.py

runes:
	docker run -d --name es \
	  -p 9200:9200 -p 9300:9300 \
	  -e discovery.type=single-node \
	  -e xpack.security.enabled=false \
          -v /Users/markmalamut/esdata:/usr/share/elasticsearch/data \
	  elasticsearch:8.12.2
