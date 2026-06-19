PYTHON ?= python

.PHONY: setup infra-up infra-down scrape consume sentiment vector eval timeseries run-all run-fast

setup:
	$(PYTHON) -m pip install -r requirements.txt

infra-up:
	docker compose up -d

infra-down:
	docker compose down

scrape:
	$(PYTHON) scrapers/sbv_scraper.py
	$(PYTHON) scrapers/cafef_scraper.py

consume:
	$(PYTHON) pipeline/kafka_consumer.py

sentiment:
	$(PYTHON) ai_engine/sentiment_analyzer.py

vector:
	$(PYTHON) database/vector_store.py

eval:
	$(PYTHON) evaluation/run_evaluation.py

timeseries:
	$(PYTHON) -c "from time_series.pipeline import TimeSeriesPipeline as P; p=P('mongodb://localhost:27017/','sentiment','clean_news'); p.run_and_export(days_back=30, export_path='output/sentiment_dashboard.json')"

run-all:
	$(PYTHON) scripts/run_pipeline.py

run-fast:
	$(PYTHON) scripts/run_pipeline.py --skip-eval --consumer-drain-seconds 10
