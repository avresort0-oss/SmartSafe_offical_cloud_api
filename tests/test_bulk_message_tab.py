import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ui.bulk_message_tab import BulkMessageTab


class NormalizeRecipientsTests(unittest.TestCase):
    def test_normalizes_and_deduplicates_common_phone_formats(self):
        raw = "+1 555 000 1234\n(44)-7700-900123\n15550001234\n"

        phones, invalid_lines, duplicate_count = BulkMessageTab._normalize_recipients(raw)

        self.assertEqual(phones, ["15550001234", "447700900123"])
        self.assertEqual(invalid_lines, [])
        self.assertEqual(duplicate_count, 1)

    def test_rejects_invalid_recipient_lines(self):
        raw = "abc\n123\n1234567890123456\n+12x34\n"

        phones, invalid_lines, duplicate_count = BulkMessageTab._normalize_recipients(raw)

        self.assertEqual(phones, [])
        self.assertEqual(invalid_lines, ["abc", "123", "1234567890123456", "+12x34"])
        self.assertEqual(duplicate_count, 0)

    def test_ignores_blanks_and_counts_duplicate_after_normalization(self):
        raw = "\n  \n+8801712345678\n8801712345678\n"

        phones, invalid_lines, duplicate_count = BulkMessageTab._normalize_recipients(raw)

        self.assertEqual(phones, ["8801712345678"])
        self.assertEqual(invalid_lines, [])
        self.assertEqual(duplicate_count, 1)


if __name__ == "__main__":
    unittest.main()
