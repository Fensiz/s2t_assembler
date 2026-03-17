PYTHON ?= python3
APP_NAME ?= s2t-tool
DIST_DIR ?= dist
BUILD_DIR ?= .
STAGING_DIR ?= .build_py
RELEASES_DIR ?= ../s2t-tools-pyz

PYZ_FILE := $(DIST_DIR)/$(APP_NAME).pyz
APP_VERSION := $(shell $(PYTHON) -c "from app_info import APP_VERSION; print(APP_VERSION)")
VERSIONED_PYZ_FILE := $(RELEASES_DIR)/$(APP_NAME)-$(APP_VERSION).pyz
LATEST_JSON := $(RELEASES_DIR)/latest.json

.PHONY: all clean prepare pyz deploy

all: pyz

clean:
	rm -rf $(DIST_DIR) $(STAGING_DIR)

$(DIST_DIR):
	mkdir -p $(DIST_DIR)

prepare:
	rm -rf $(STAGING_DIR)
	mkdir -p $(STAGING_DIR)

	rsync -av \
        --exclude='.git/' \
        --exclude='.idea/' \
        --exclude='.venv/' \
        --exclude='.build/' \
        --exclude='.build_py/' \
        --exclude='dist/' \
        --exclude='repo/' \
        --exclude='__pycache__/' \
        --exclude='__main__.py' \
        --include='*/' \
        --include='*.py' \
        --include='*.json' \
        --exclude='*' \
        ./ .build_py/

pyz: prepare $(DIST_DIR)
	$(PYTHON) -m zipapp $(STAGING_DIR) \
		-o $(PYZ_FILE) \
		-m "ui:main_ui"

deploy: pyz
	mkdir -p $(RELEASES_DIR)
	cp $(PYZ_FILE) $(VERSIONED_PYZ_FILE)
	$(PYTHON) -c 'import json; from pathlib import Path; from app_info import APP_VERSION; p = Path("$(LATEST_JSON)"); data = {"version": APP_VERSION, "path": "$(APP_NAME)-" + APP_VERSION + ".pyz"}; p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")'
	@echo "Deployed: $(VERSIONED_PYZ_FILE)"
	@echo "Updated:  $(LATEST_JSON)"