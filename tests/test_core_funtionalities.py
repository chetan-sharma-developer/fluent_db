import pytest
from fluent_db import Table, Integer, Char, Timestamp

class AdvancedUser(Table):
    def __init__(self):
        super().__init__()
        self.columns = [
            Integer("id").primary(),
            Char("name"),
            Timestamp("created_at").useCurrent()
        ]

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "advanced_test.db"
    return str(db_file)

def test_update_record(test_db):
    user = AdvancedUser()
    user.database = test_db
    user.createTable()
    
    user.insert({
        "id": 101,
        "name": "Initial Name",
        "created_at": "2025-05-25 09:00:00"
    })
    # Update the record where id == 101
    user.where("id", 101).update({"name": "Updated Name"})
    record = user.where("id", 101).first()
    assert record["name"] == "Updated Name"

def test_delete_record(test_db):
    user = AdvancedUser()
    user.database = test_db
    user.createTable()
    
    user.insert({
        "id": 102,
        "name": "Delete Me",
        "created_at": "2025-05-25 09:30:00"
    })
    # Delete the record where id == 102
    user.where("id", 102).delete()
    record = user.where("id", 102).first()
    assert record is None

def test_complex_where_query(test_db):
    user = AdvancedUser()
    user.database = test_db
    user.createTable()
    
    # Insert multiple records
    records = [
        {"id": 201, "name": "Alice", "created_at": "2025-05-25 10:00:00"},
        {"id": 202, "name": "Bob", "created_at": "2025-05-25 10:05:00"},
        {"id": 203, "name": "Charlie", "created_at": "2025-05-25 10:10:00"}
    ]
    for rec in records:
        user.insert(rec)
        
    # Retrieve records with id greater than 201
    # Assuming the where method supports comparison operators if a third argument is given.
    result = user.where("id", 201, ">").get()
    assert len(result) == 2
    ids = [r["id"] for r in result]
    assert 202 in ids and 203 in ids

# Rollback functionality is not implemented in the provided code in current version.
# def test_transaction_management(test_db):
#     user = AdvancedUser()
#     user.database = test_db
#     user.createTable()
    
#     # Test transaction rollback on error
#     try:
#         user.beginTransaction()
#         user.insert({
#             "id": 301,
#             "name": "Transaction Test",
#             "created_at": "2025-05-25 11:00:00"
#         })
#         # Simulate an error in the transaction
#         raise RuntimeError("Simulated error")
#         user.commit()
#     except RuntimeError:
#         user.rollback()
    
#     # After rollback, the record should not exist
#     record = user.where("id", 301).first()
#     assert record is None