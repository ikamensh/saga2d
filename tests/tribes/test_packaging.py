"""The frozen diagnostic and package description, checked before anything is built."""
import importlib.util

from saga2d.packaging.verify import local_server
from tools.package_tribes import PACKAGE


def package_check():
    spec = importlib.util.spec_from_file_location("tribes_package_check", PACKAGE.check)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    return checker


def test_package_names_existing_entry_documents_and_diagnostics():
    assert PACKAGE.check.is_file()
    assert (PACKAGE.root / PACKAGE.package / "__main__.py").is_file()
    for origin in PACKAGE.documents.values():
        assert (PACKAGE.root / origin).is_file(), origin


def test_shipped_smoke_exchanges_authoritative_turns_and_rejoins():
    with local_server(PACKAGE.online) as endpoint:
        result = package_check().online_smoke(endpoint)
    assert result == {"create_join": True, "foreign_turn_rejected": True, "authoritative_turns": True,
                      "private_seat_rejoin": True}
