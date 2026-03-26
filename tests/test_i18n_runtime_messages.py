from __future__ import annotations

import unittest

from s2t_tool.adapters.ui.i18n import localize_runtime_message


class RuntimeMessageLocalizationTests(unittest.TestCase):
    def test_localizes_conflicting_mapping_attribute_names(self) -> None:
        source = (
            "Conflicting attribute_name inside table 'registry' "
            "for attribute_code 'sid': ['Описание 1', 'Описание 2']"
        )
        result = localize_runtime_message(source, "ru")
        self.assertEqual(
            result,
            "Лист Mappings: для таблицы 'registry' у атрибута 'sid' заданы разные описания: ['Описание 1', 'Описание 2']",
        )

    def test_localizes_mappings_row_error(self) -> None:
        source = "Mappings row must contain load_code, table_name, attribute_code"
        result = localize_runtime_message(source, "ru")
        self.assertEqual(
            result,
            "На листе Mappings в строке должны быть заполнены load_code, table_name и attribute_code.",
        )


if __name__ == "__main__":
    unittest.main()
