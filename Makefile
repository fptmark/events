all: er setup code test 

clean: 
	rm -rf backup/app
	mv app backup

code: schema.yaml
	rm -rf backup/app
	mv app backup || true
	python generators/gen_models.py schema.yaml
	python generators/gen_routes.py schema.yaml
	python generators/gen_main.py schema.yaml
	python generators/gen_db.py schema.yaml
	cp -f config.json app

setup: requirements.txt
	pip install -r requirements.txt

er: schema.mmd
	mmdc -i schema.mmd -o schema.png

app/main.py: schema.yaml

test: app/main.py
	PYTHONPATH=. python app/main.py
