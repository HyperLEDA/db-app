test:
	python -m unittest discover -s tests/domain -p "*Test.py"

install:
	python -m pip install -r requirements.txt

runserver:
	python main.py runserver
