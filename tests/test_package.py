import eoapi_client


def test_version():
    assert isinstance(eoapi_client.__version__, str)
