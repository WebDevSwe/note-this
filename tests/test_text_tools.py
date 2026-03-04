from notethis import text_tools


def test_parse_participant_list_quotes_and_emails() -> None:
    text = "\"Felicia Strömberg\" <felicia@sbab.se>; \"Monica Sandgren\" <monica@sbab.se>"
    assert text_tools.parse_participant_list(text) == ["Felicia Strömberg", "Monica Sandgren"]


def test_parse_participant_list_fallback_split() -> None:
    text = "Anna Andersson, Bertil Berg; Cecilia Ceder"
    assert text_tools.parse_participant_list(text) == ["Anna Andersson", "Bertil Berg", "Cecilia Ceder"]
