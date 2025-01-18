all: code setup er test 

code: generator.py
	rm -rf app
	python generator.py
	mv events app

setup: requirements.txt
	pip install -r app/requirements.txt

er: events.mmd
	mmdc -i events.mmd -o events.png

test:
	echo "open app: http:/127.0.0.1:8000"
	echo "Swagger: http:/127.0.0.1:8000/docs"
	echo "Redoc: http:/127.0.0.1:8000/redoc"
	PYTHONPATH=. uvicorn app.main:app --reload
