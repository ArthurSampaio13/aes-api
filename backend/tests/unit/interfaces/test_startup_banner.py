import pyfiglet


def test_aes_api_banner_renders_recognizable_text():
    banner = pyfiglet.figlet_format("AES-API")
    assert "AES-API" not in banner
    assert len(banner.strip()) > 0
    assert banner.count("\n") > 1
