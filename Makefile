.PHONY: install spend value report weekly clean

install:
	python3 -m venv .venv
	./.venv/bin/pip install -e .

spend:
	./.venv/bin/avt-spend --days 30 --out out/spend.csv

value:
	./.venv/bin/avt-value --days 30 --out out/value.csv

report: spend value
	./.venv/bin/avt-report --spend out/spend.csv --value out/value.csv --out out/report.csv --chart out/chart.png

weekly:
	./bin/avt-weekly

clean:
	rm -rf out/ build/ dist/ *.egg-info
