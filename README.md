# Fluent DB

Fluent DB is a Python library that provides a fluent interface for database operations, inspired by Laravel ORM's DB handling. If you're looking for an intuitive and expressive way to build and execute SQL queries, Fluent DB offers one of the best approaches available in Python.

## Features

- **Fluent API:** Build SQL queries using clean, chainable methods.
- **Relationships:** Define one-to-one and one-to-many relationships between tables effortlessly.
- **Elegant Query Building:** Use methods like `where`, `orWhere`, `order_by`, `limit`, and `offset` to create complex queries.
- **Dynamic Table Creation and Data Manipulation:** Automate table creation and perform insert, update, and delete operations.
- **Flexible Data Types:** Support for multiple data types including `Integer`, `Decimal`, `Char`, `Varchar`, `Text`, and more.
- **Inspired by Laravel:** Designed after Laravel's ORM to provide a smooth and familiar experience.

## Installation

Install Fluent DB via pip:

```bash
pip install fluent_db
```

## Usage Examples

### Defining a Table

```python
from fluent_db import Table, Integer, Char, Timestamp

class User(Table):
    def __init__(self):
        super().__init__()
        self.columns = [
            Integer("id").primary(),
            Char("name"),
            Timestamp("created_at").useCurrent()
        ]

# Create the users table
user_table = User()
user_table.createTable()
```

### Inserting Data

```python
# Insert a new record into the User table
user = User()
user.insert({
    "id": 1,
    "name": "John Doe",
    "created_at": "2025-05-25 10:00:00"
})
```

### Querying Data

```python
# Retrieve users with the name 'John Doe'
users = User().where("name", "John Doe").get()
print(users)
```

### Updating Data

```python
# Update user record where id equals 1
user = User()
user.where("id", 1).update({
    "name": "Jane Doe"
})
```

### Deleting Data

```python
# Delete user record where id equals 1
user = User()
user.where("id", 1).delete()
```

## License

Fluent DB is licensed under the MIT License.
```# filepath: c:\opensource\fluent_db\README.md
# Fluent DB

Fluent DB is a Python library that provides a fluent interface for database operations, inspired by Laravel ORM's DB handling. If you're looking for an intuitive and expressive way to build and execute SQL queries, Fluent DB offers one of the best approaches available in Python.

## Features

- **Fluent API:** Build SQL queries using clean, chainable methods.
- **Relationships:** Define one-to-one and one-to-many relationships between tables effortlessly.
- **Elegant Query Building:** Use methods like `where`, `orWhere`, `order_by`, `limit`, and `offset` to create complex queries.
- **Dynamic Table Creation and Data Manipulation:** Automate table creation and perform insert, update, and delete operations.
- **Flexible Data Types:** Support for multiple data types including `Integer`, `Decimal`, `Char`, `Varchar`, `Text`, and more.
- **Inspired by Laravel:** Designed after Laravel's ORM to provide a smooth and familiar experience.

## Installation

Install Fluent DB via pip:

```bash
pip install fluent-db
```

## Usage Examples

### Defining a Table

```python
from fluent_db import Table, Integer, Char, Timestamp

class User(Table):
    def __init__(self):
        super().__init__()
        self.columns = [
            Integer("id").primary(),
            Char("name"),
            Timestamp("created_at").useCurrent()
        ]

# Create the users table
user_table = User()
user_table.createTable()
```

### Inserting Data

```python
# Insert a new record into the User table
user = User()
user.insert({
    "id": 1,
    "name": "John Doe",
    "created_at": "2025-05-25 10:00:00"
})
```

### Querying Data

```python
# Retrieve users with the name 'John Doe'
users = User().where("name", "John Doe").get()
print(users)
```

### Updating Data

```python
# Update user record where id equals 1
user = User()
user.where("id", 1).update({
    "name": "Jane Doe"
})
```

### Deleting Data

```python
# Delete user record where id equals 1
user = User()
user.where("id", 1).delete()
```

### custom database location

```python
# Define a base class with custom database location
class MyDatabase(Table):
    def __init__(self):
        super().__init__()
        self.database = "/path/to/my_database.sqlite3"  # Set your custom DB path here

# Define a table using the custom DB base
class Student(MyDatabase):
    def __init__(self):
        super().__init__()
        self.columns = [
            Integer("id").primary(),
            Char("name"),
            Timestamp("created_at").useCurrent()
        ]

class Teacher(MyDatabase):
    def __init__(self):
        super().__init__()
        self.columns = [
            Integer("id").primary(),
            Char("name"),
            Timestamp("created_at").useCurrent()
        ]
```
## License

Fluent DB is licensed under the MIT License.
