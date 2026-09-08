import unittest
from pyqttier.contenttype import ContentType


class TestContentType(unittest.TestCase):
    def test_standard_text_html_with_charset(self):
        """Standard text/html with charset parameter"""
        ct = ContentType("text/html; charset=utf-8")

        self.assertEqual(str(ct), "text/html")
        self.assertEqual(ct, "text/html")
        self.assertEqual(ct.charset, "utf-8")
        self.assertEqual(ct.upper(), "TEXT/HTML")

    def test_multipart_form_data_with_quoted_boundary(self):
        """Multipart form-data with quoted boundary and ttl parameters"""
        header = 'multipart/form-data; boundary="---WebKitFormBoundary7MA4YWxk"; ttl=30'
        ct = ContentType(header)

        self.assertEqual(str(ct), "multipart/form-data")
        self.assertEqual(ct.boundary, "---WebKitFormBoundary7MA4YWxk")
        self.assertEqual(ct.ttl, "30")

    def test_simple_content_type_no_parameters(self):
        """Content type with no parameters defaults to standard string behavior"""
        ct = ContentType("application/json")

        self.assertEqual(str(ct), "application/json")
        self.assertFalse(hasattr(ct, "charset"))
        self.assertEqual(ct.parameters, {})

    def test_content_type_is_string_subclass(self):
        """ContentType is a str subclass and supports string methods"""
        ct = ContentType("text/plain")

        self.assertIsInstance(ct, str)
        self.assertEqual(ct.upper(), "TEXT/PLAIN")
        self.assertTrue(ct.startswith("text"))

    def test_empty_content_type_raises_error(self):
        """Empty or whitespace-only Content-Type raises ValueError"""
        with self.assertRaises(ValueError):
            ContentType("")

        with self.assertRaises(ValueError):
            ContentType("   ")

    def test_invalid_content_type_format_raises_error(self):
        """Content-Type without '/' raises ValueError"""
        with self.assertRaises(ValueError):
            ContentType("invalid")

    def test_parameters_dict_access(self):
        """Parameters can be accessed via parameters dict"""
        ct = ContentType("text/html; charset=utf-8; boundary=test")

        self.assertEqual(ct.parameters["charset"], "utf-8")
        self.assertEqual(ct.parameters["boundary"], "test")
        self.assertEqual(len(ct.parameters), 2)

    def test_case_insensitive_parsing(self):
        """Content-Type and parameters are parsed case-insensitively"""
        ct = ContentType("TEXT/HTML; CHARSET=utf-8")

        self.assertEqual(str(ct), "text/html")
        self.assertEqual(ct.charset, "utf-8")

    def test_construct_from_existing_content_type_clones_parameters(self):
        """Constructing from an existing ContentType clones its parameters"""
        original = ContentType("text/html; charset=utf-8; boundary=test")
        clone = ContentType(original)

        self.assertEqual(str(clone), "text/html")
        self.assertEqual(clone.parameters, original.parameters)
        self.assertEqual(clone.charset, "utf-8")
        self.assertEqual(clone.boundary, "test")

    def test_construct_from_existing_content_type_is_independent_copy(self):
        """Cloned parameters dict is a separate object from the original"""
        original = ContentType("text/html; charset=utf-8")
        clone = ContentType(original)

        self.assertIsNot(clone.parameters, original.parameters)

    def test_to_header_no_parameters(self):
        """to_header returns just the type/subtype when there are no parameters"""
        ct = ContentType("application/json")

        self.assertEqual(ct.to_header(), "application/json")

    def test_to_header_unquoted_parameter(self):
        """to_header leaves simple parameter values unquoted"""
        ct = ContentType("text/html; charset=utf-8")

        self.assertEqual(ct.to_header(), "text/html; charset=utf-8")

    def test_to_header_leaves_simple_boundary_unquoted(self):
        """to_header omits quotes for values with no characters requiring them"""
        ct = ContentType(
            'multipart/form-data; boundary="---WebKitFormBoundary7MA4YWxk"'
        )

        self.assertEqual(
            ct.to_header(),
            "multipart/form-data; boundary=---WebKitFormBoundary7MA4YWxk",
        )

    def test_to_header_quotes_values_with_special_characters(self):
        """to_header quotes parameter values containing whitespace, quotes, ';' or '='"""
        ct = ContentType('text/plain; label="hello world"')

        self.assertEqual(
            ct.to_header(),
            'text/plain; label="hello world"',
        )

    def test_to_header_round_trips_through_content_type(self):
        """Reconstructed header can be parsed again into an equivalent ContentType"""
        original = ContentType(
            'multipart/form-data; boundary="---WebKitFormBoundary7MA4YWxk"; ttl=30'
        )
        roundtripped = ContentType(original.to_header())

        self.assertEqual(original, roundtripped)
        self.assertEqual(original.parameters, roundtripped.parameters)

    def test_to_header_escapes_embedded_quotes(self):
        """to_header escapes embedded double quotes in quoted values"""
        ct = ContentType('text/plain; label="say \\"hi\\""')

        self.assertEqual(ct.label, 'say "hi"')

        header = ct.to_header()
        reparsed = ContentType(header)

        self.assertEqual(reparsed.label, ct.label)


if __name__ == "__main__":
    unittest.main()
