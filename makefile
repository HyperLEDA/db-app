test:
	python -m unittest discover -s tests -p "*_test.py" -v

install:
	python -m pip install -r requirements.txt

runserver:
	python main.py runserver -c configs/dev/config.yaml
