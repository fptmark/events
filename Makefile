all: code setup er test 

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

test: setup app/main.py
	echo "open app: http:/127.0.0.1:8000"
	echo "Swagger: http:/127.0.0.1:8000/docs"
	echo "Redoc: http:/127.0.0.1:8000/redoc"
	PYTHONPATH=. uvicorn app.main:app --reload
