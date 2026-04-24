PYTHON ?= python3
APP_NAME ?= s2t-tool
DIST_DIR ?= dist
STAGING_DIR ?= .build_py
RELEASES_DIR ?= ../s2t-tools-pyz

PYZ_FILE := $(DIST_DIR)/$(APP_NAME).pyz
APP_VERSION := $(shell $(PYTHON) -c "from s2t_tool.app_info import APP_VERSION; print(APP_VERSION)")
VERSIONED_PYZ_FILE := $(RELEASES_DIR)/$(APP_NAME)-$(APP_VERSION).pyz
LATEST_JSON := $(RELEASES_DIR)/latest.json
RUNTIME_FILES := app_config.json metadata.json writer_config.json

.PHONY: all clean prepare test check pyz deploy

all: pyz

clean:
	rm -rf $(DIST_DIR) $(STAGING_DIR)

test:
	$(PYTHON) -m unittest discover -s tests -v

check: test
	PYTHONPYCACHEPREFIX=/tmp/pycache $(PYTHON) -m py_compile $$(find s2t_tool -name '*.py' | sort)

$(DIST_DIR):
	mkdir -p $(DIST_DIR)

prepare:
	rm -rf $(STAGING_DIR)
	mkdir -p $(STAGING_DIR)

	rsync -av \
		--exclude='__pycache__/' \
		--exclude='.DS_Store' \
		s2t_tool/ \
		$(STAGING_DIR)/s2t_tool/

	cp $(RUNTIME_FILES) $(STAGING_DIR)/

pyz: prepare $(DIST_DIR)
	$(PYTHON) -m zipapp $(STAGING_DIR) \
		-o $(PYZ_FILE) \
		-m "s2t_tool.adapters.ui.app:main_ui"

deploy: pyz
	mkdir -p $(RELEASES_DIR)
	cp $(PYZ_FILE) $(VERSIONED_PYZ_FILE)
	$(PYTHON) -c 'import json; from pathlib import Path; from s2t_tool.app_info import APP_VERSION; p = Path("$(LATEST_JSON)"); data = {"version": APP_VERSION, "path": "$(APP_NAME)-" + APP_VERSION + ".pyz"}; p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")'
	@echo "Deployed: $(VERSIONED_PYZ_FILE)"
	@echo "Updated:  $(LATEST_JSON)"
