from app.services.normalization import normalize_address, normalize_vendor_name


def test_vendor_suffixes_and_punctuation_stripped():
    assert normalize_vendor_name("Example Widgets, LLC.") == "example widgets"
    assert normalize_vendor_name("SAMPLE PAVING CO") == "sample paving"


def test_vendor_variants_converge():
    a = normalize_vendor_name("Acme Fictional Corp.")
    b = normalize_vendor_name("ACME FICTIONAL CORPORATION")
    assert a == b == "acme fictional"


def test_address_normalization_is_stable():
    a = normalize_address("123 Main St., Suite 4")
    b = normalize_address("123  MAIN ST SUITE 4")
    assert a == b == "123 main st suite 4"
