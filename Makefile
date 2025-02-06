.PHONY: clean code

all: setup code test 

gen: code test

schema: schema.yaml schema.png

clean: 
	rm -rf app schema.yaml app.log
	mkdir app
	cp config.json app

models: generators/gen_models.py schema generators/templates/models/*
	rm -rf app/models
	python generators/gen_models.py schema.yaml .

routes: generators/gen_routes.py schema generators/templates/routes/*
	rm -rf app/routes
	python generators/gen_routes.py schema.yaml .

main: generators/gen_main.py schema generators/templates/main/*
	rm -f app/main.py
	python generators/gen_main.py schema.yaml .

db: generators/gen_db.py schema generators/templates/db/*
	rm -rf app/db.py
	python generators/gen_db.py schema.yaml .


code: generators/*.py schema.yaml generators/templates/* 
	python generators/gen_models.py schema.yaml .
	python generators/gen_routes.py schema.yaml .
	python generators/gen_main.py schema.yaml .
	python generators/gen_db.py schema.yaml .
	cp -r utilities app

setup: requirements.txt
	pip install -r requirements.txt

schema.yaml: schema.mmd schemaConvert.py
	python schemaConvert.py

schema.png: schema.mmd
	mmdc -i schema.mmd -o schema.png

app/main.py: schema.yaml

test: app/main.py
	PYTHONPATH=. python app/main.py
