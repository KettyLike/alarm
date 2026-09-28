from user_locations import UserLocationStore


def test_locations_are_isolated_and_persisted_per_chat(tmp_path) -> None:
    database_path = tmp_path / "locations.sqlite3"
    store = UserLocationStore(database_path)
    store.set("101", 50.45, 30.52)
    store.set("202", 49.84, 24.03)

    restored_store = UserLocationStore(database_path)

    assert restored_store.get("101") == (50.45, 30.52)
    assert restored_store.get("202") == (49.84, 24.03)
    assert restored_store.get("303") is None