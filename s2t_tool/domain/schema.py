from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class S2TSchema:
    change_history_sheet: str = "Change history"
    source_lg_sheet: str = "Source LG"
    targets_sheet: str = "Targets"
    pre_transforms_sheet: str = "Pre-transforms"
    joins_sheet: str = "Joins"
    mappings_sheet: str = "Mappings"
    settings_sheet: str = "Settings"
    parameters_sheet: str = "Parameters"
    st_decoder_sheet: str = "ST_DECODER"
    st_filter_sheet: str = "ST_FILTER"
    metadata_sheet: str = "Metadata"

    change_history_json: str = "change-history.json"
    source_lg_csv: str = "source-lg.csv"
    targets_csv: str = "targets.csv"
    settings_csv: str = "settings.csv"
    parameters_csv: str = "parameters.csv"
    st_decoder_csv: str = "st_decoder.csv"
    st_filter_csv: str = "st_filter.csv"
    metadata_json: str = "metadata.json"
    attribute_names_json: str = "attribute_names.json"
    mappings_csv: str = "mappings.csv"
    mappings_extra_json: str = "mappings.extra.json"

    pre_transforms_dir: str = "pre-transforms"
    joins_dir: str = "joins"

    source_lg_headers: tuple[str, ...] = (
        "scheme",
        "table",
        "column",
        "data_type",
        "data_length",
        "is_key",
        "description",
        "link",
    )
    targets_headers: tuple[str, ...] = ("table_code", "table_name")
    settings_headers: tuple[str, ...] = (
        "settings_alias",
        "settings_description",
        "settings_table",
        "settings_type",
        "period",
        "mask",
    )
    parameters_headers: tuple[str, ...] = ("parameter", "value", "data_type", "comment")
    st_filter_headers: tuple[str, ...] = (
        "settings_type",
        "source_value",
        "target_value",
        "start_dt",
        "end_dt",
        "update_date",
        "author_update_name",
    )
    sheet_aliases: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "Change history": (
                "Change history",
                "Change History",
                "ChangeHistory",
                "Change history ",
            ),
            "Source LG": (
                "Source LG",
                "SourceLG",
                "Sources LG",
                "SourcesLG",
            ),
            "Targets": ("Targets", "Target"),
            "Pre-transforms": (
                "Pre-transforms",
                "Pre transforms",
                "PreTransforms",
                "Pre-Transforms",
            ),
            "Joins": ("Joins", "Join"),
            "Mappings": ("Mappings", "Mapping"),
            "Settings": ("Settings", "Setting"),
            "Parameters": ("Parameters", "Parameter"),
            "ST_DECODER": ("ST_DECODER", "ST DECODER", "ST-DECODER", "Decoder"),
            "ST_FILTER": ("ST_FILTER", "ST FILTER", "ST-FILTER", "Filter"),
            "Metadata": ("Metadata", "MetaData", "Meta Data"),
        }
    )

    def sheet_aliases_for(self, sheet_name: str) -> tuple[str, ...]:
        return self.sheet_aliases.get(sheet_name, (sheet_name,))

    @staticmethod
    def normalize_sheet_name(value: str) -> str:
        return "".join(str(value).strip().lower().split())


DEFAULT_SCHEMA = S2TSchema()

