.PHONY: clean move save code

all: er setup code test 

clean: 
	rm -rf backup/app
	mv app backup

move:
	rm -rf app
	mv code/app app
	cp -f config.json app

save:
	rm -rf backup/app
	mv app backup || true

code: 
	rm -rf code
	python generators/gen_models.py schema.yaml code
	python generators/gen_routes.py schema.yaml code
	python generators/gen_main.py schema.yaml code
	python generators/gen_db.py schema.yaml code
	python generators/gen_helpers.py code

setup: requirements.txt
	pip install -r requirements.txt

er: schema.mmd
	mmdc -i schema.mmd -o schema.png

app/main.py: schema.yaml

test: app/main.py
	PYTHONPATH=. python app/main.py
