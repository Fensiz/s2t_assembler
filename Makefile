PYTHON ?= python3
APP_NAME ?= s2t-tool
BUILD_DIR ?= .build/pyz-src
DIST_DIR ?= dist
PYZ_FILE := $(DIST_DIR)/$(APP_NAME).pyz

SOURCES = \
	__main__.py \
	app_info.py \
	ui.py \
	ui_app.py \
	ui_models.py \
	ui_recent_store.py \
	ui_utils.py \
	ui_view.py \
	main.py \
	main_branching.py \
	main_config.py \
	main_files.py \
	main_models.py \
	main_service.py \
	main_versioning.py \
	reader.py \
	writer.py \
	common.py \
	InitialSetupService.py \
	UpdateService.py \
	git_repo.py \
	metadata.json \
	writer_config.json \
	app_config.json

.PHONY: all build clean run help

all: build

help:
	@echo "Targets:"
	@echo "  make build   - build dist/$(APP_NAME).pyz"
	@echo "  make run     - run built pyz"
	@echo "  make clean   - remove build artifacts"

build: clean
	@mkdir -p $(BUILD_DIR)
	@mkdir -p $(DIST_DIR)
	@for f in $(SOURCES); do cp $$f $(BUILD_DIR)/; done
	$(PYTHON) -m zipapp $(BUILD_DIR) -o $(PYZ_FILE)
	@echo "Built: $(PYZ_FILE)"

run: build
	$(PYTHON) $(PYZ_FILE)

clean:
	@rm -rf $(BUILD_DIR) $(DIST_DIR)
