S2R_DIR ?= ~/Projects/schema2rest
GENERICS = $(S2R_DIR)/src/server_generic_files
GENERATOR_DIR = $(S2R_DIR)/generators
CONVERTER_DIR = $(S2R_DIR)/convert
PYPATH = PYTHONPATH=~/Projects/schema2rest
BACKEND ?= mongo
PROJECT_NAME ?= "Project Name Here"
ES_DATA_DIR ?= $(HOME)/esdata

.PHONY: clean code cli install setup test run help

# Help target
help:
	@echo "Available targets:"
	@echo ""
	@echo "Setup targets:"
	@echo "  install     - Full setup: install dependencies, clean, and rebuild everything"
	@echo "  setup       - Install Python dependencies and system packages (mongo, redis)"
	@echo ""
	@echo "User targets (running the application):"
	@echo "  run         - Run server with default backend ($(BACKEND))"
	@echo "  runmongo    - Run server with MongoDB backend"
	@echo "  startes     - Start Elasticsearch in Docker"
	@echo "  runes       - Run server with current backend"
	@echo "  test        - Run tests"
	@echo "  cli         - Run command-line interface"
	@echo "  redis       - Start Redis service"
	@echo ""
	@echo "Developer targets (code generation - requires S2R_DIR):"
	@echo "  clean       - Remove app directory and start fresh"
	@echo "  generic     - Copy server generic files"
	@echo "  firsttime   - Copy server generic files and setup config files"
	@echo "  rebuild     - Full rebuild: schema + all generators"
	@echo "  schema      - Convert schema.mmd to schema.yaml and generate diagram"
	@echo "  main        - Generate main.py"
	@echo "  models      - Generate model files"
	@echo "  services    - Generate service routes"
	@echo "  spec        - Generate OpenAPI specification"
	@echo "  code        - Generate all code (main, models, services, spec)"
	@echo ""
	@echo "Convenience targets:"
	@echo "  all         - Generate schema and all code"
	@echo "  openapi     - Alias for generating OpenAPI spec"

# Setup targets
install: setup clean rebuild

setup:	$(S2R_DIR)/requirements.txt
	pip install -r $(S2R_DIR)/requirements.txt
	brew install mongo
	brew install redis

# User targets (running the application)
run:	
	PYTHONPATH=. python app/main.py $(BACKEND).json

runmongo:	
	PYTHONPATH=. python app/main.py mongo.json 

runes:	
	PYTHONPATH=. python app/main.py es.json 

startes:
	docker run -d --name es \
	  -p 9200:9200 -p 9300:9300 \
	  -e discovery.type=single-node \
	  -e xpack.security.enabled=false \
          -v $(ES_DATA_DIR):/usr/share/elasticsearch/data \
	  elasticsearch:8.12.2

test: test.py
	pytest -s test.py

cli:
	PYTHONPATH=. python cli/cli.py

redis:
	brew services start redis

# Developer targets (code generation)
clean: 
	rm -rf app
	rm -f openapi.json

generic:
	cp -r $(GENERICS)/* app/
	mv app/requirements.txt .
	rm app/Makefile
	rm app/config/*.json

firsttime:
	cp -r $(GENERICS) app
	mv app/requirements.txt .
	rm app/Makefile
	mv app/config/*.json .

rebuild:
	$(MAKE) schema
	$(MAKE) main
	$(MAKE) models
	$(MAKE) services
	$(MAKE) spec 

schema : schema.mmd 
	$(PYPATH) python -m convert.schemaConvert schema.mmd 
	cat schema.mmd | sed '/[[:alnum:]].*%%/ s/%%.*//' | mmdc -i - -o schema.png
	$(MAKE) spec

main:
	$(PYPATH) python -m generators.gen_main schema.yaml . 

models:
	$(PYPATH) python -m generators.models.gen_model_main schema.yaml . 

services: 
	$(PYPATH) python -m generators.gen_service_routes schema.yaml $(GENERICS) .

spec:
	$(PYPATH) python -m generators.gen_openapi .

code:	schema.yaml 
	mkdir -p app/utilities
	$(MAKE) main
	$(MAKE) models
	$(MAKE) services
	$(MAKE) spec

# Convenience targets
all: schema code 
