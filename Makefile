.PHONY: clean move save code

all: setup code test 

gen: code move test

schema: schema.yaml schema.png

clean: 
	rm -rf backup/app
	mv app backup

move:
	rm -rf backup/app
	mv app backup
	mv code/app app
	cp -f config.json app

save:
	rm -rf backup/app
	mv app backup || true

models: generators/gen_models.py schema generators/templates/models/*
	rm -rf code/app/models
	python generators/gen_models.py schema.yaml code

routes: generators/gen_routes.py schema generators/templates/routes/*
	rm -rf code/app/routes
	python generators/gen_routes.py schema.yaml code

main: generators/gen_main.py schema generators/templates/main/*
	rm -f code/app/main.py
	python generators/gen_main.py schema.yaml code

db: generators/gen_db.py schema generators/templates/db/*
	rm -rf code/app/db.py
	python generators/gen_db.py schema.yaml code


code: generators/*.py schema.yaml generators/templates/* 
	rm -rf code
	python generators/gen_models.py schema.yaml code
	python generators/gen_routes.py schema.yaml code
	python generators/gen_main.py schema.yaml code
	python generators/gen_db.py schema.yaml code
	mkdir code/app/utilities
	cp utilities/config.py code/app/utilities/config.py

setup: requirements.txt
	pip install -r requirements.txt

schema.yaml: schema.mmd schemaConvert.py
	python schemaConvert.py

schema.png: schema.mmd
	mmdc -i schema.mmd -o schema.png

app/main.py: schema.yaml

test: app/main.py
	PYTHONPATH=. python app/main.py
