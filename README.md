# Fluent DB

[![PyPI version](https://badge.fury.io/py/fluent-db.svg)](https://badge.fury.io/py/fluent-db)

Fluent DB is a Python library that provides an intuitive, fluent, and ORM-like interface for interacting with SQLite databases. It aims to simplify database operations by allowing you to define your schema and query your data using Pythonic expressions and method chaining.

## Features

*   **Fluent Query Builder:** Construct SQL queries using a clean, chainable API.
*   **Schema Definition as Code:** Define your database tables and columns as Python classes and attributes.
*   **CRUD Operations:** Easily perform Create, Read, Update, and Delete operations.
*   **Relationship Support:** Define and query `hasOne` and `hasMany` relationships between tables.
*   **Automatic Table Creation:** Generate `CREATE TABLE` statements from your model definitions.
*   **SQLite Support:** Built-in connector for SQLite.
*   **Data Type Abstractions:** Rich set of column types (`Id`, `Char`, `Varchar`, `Timestamp`, `Integer`, `Decimal`, `Boolean`, `Text`, `LongText`) with constraints like `nullable`, `default`, `unique`, `primary_key`, `auto_increment`.
*   **Nested Conditions:** Build complex `WHERE` clauses with nested `AND`/`OR` logic.
*   **Flexible Querying:** Support for `ORDER BY`, `LIMIT`, `OFFSET`, `DISTINCT`, `WHERE IN`.
*   **Automatic Timestamp Handling:** Easily set `DEFAULT CURRENT_TIMESTAMP` and update timestamps on record changes.

## Installation

You can install Fluent DB using pip:

```bash
pip install fluent-db
```

## Quick Start

Here's a simple example to get you started:

```python
import datetime
from fluent_db import Table, Id, Char, Timestamp, SQLiteConnector

# 1. Define your database connector (optional, defaults to 'database.db')
# connector = SQLiteConnector('my_app.db')

class User(Table):
    def __init__(self, db_connector=None):
        # Pass a specific connector or let it use the default
        super().__init__(db_connector or SQLiteConnector('database.db'))
        self.columns = [
            Id("id"), # Automatically primary key, integer
            Char("name", size=100).unique(),
            Timestamp("created_at").useCurrent(), # Defaults to CURRENT_TIMESTAMP
            Timestamp("updated_at").useCurrent().useCurrentOnUpdate() # Also updates on record update
        ]

# 2. Initialize your table object
user_table = User()

# 3. Create the table in the database if it doesn't exist
user_table.createTable()
print("User table created (if it didn't exist).")

# 4. Insert data
try:
    user_table.insert({
        "name": "Alice"
    })
    user_table.insert({
        "name": "Bob"
    })
    print("Inserted Alice and Bob.")
except Exception as e:
    print(f"Error inserting data (might already exist if name is unique): {e}")

# 5. Query data
print("\nAll users:")
all_users = User().get() # Creates a new instance for querying
for user in all_users:
    print(user)
# Example output:
# {'id': 1, 'name': 'Alice', 'created_at': 'YYYY-MM-DD HH:MM:SS', 'updated_at': 'YYYY-MM-DD HH:MM:SS'}
# {'id': 2, 'name': 'Bob', 'created_at': 'YYYY-MM-DD HH:MM:SS', 'updated_at': 'YYYY-MM-DD HH:MM:SS'}
# (Timestamps will be current at the time of insertion/update)

print("\nFind Alice:")
alice = User().where("name", "Alice").first()
print(alice)
# Example output:
# {'id': 1, 'name': 'Alice', 'created_at': 'YYYY-MM-DD HH:MM:SS', 'updated_at': 'YYYY-MM-DD HH:MM:SS'}

# 6. Update data
if alice:
    User().where("id", alice['id']).update({"name": "Alice Smith"})
    print(f"\nUpdated Alice to Alice Smith. Check updated_at timestamp.")
    updated_alice = User().where("id", alice['id']).first()
    print(updated_alice)

# 7. Delete data
User().where("name", "Bob").delete()
print("\nDeleted Bob.")

print("\nAll users after delete:")
remaining_users = User().get()
for user in remaining_users:
    print(user)

# 8. Disconnect (important for SQLite to release file locks if needed,
#    though individual operations often handle their connections)
#    The provided code example doesn't explicitly require a manual top-level disconnect
#    if each operation opens/closes, but if you hold a connector instance:
# user_table.database_connector.disconnect()
# Or, if you used a shared connector:
# connector.disconnect()
```

## API Overview

### Defining Tables (Models)

Inherit from `fluent_db.Table` and define your columns in the `self.columns` list within the `__init__` method.

```python
from fluent_db import Table, Id, Char, Integer, Timestamp, SQLiteConnector

class Product(Table):
    def __init__(self, db_connector=None):
        super().__init__(db_connector or SQLiteConnector('products.db')) # Specify DB file
        self.table_name = "products" # Optional: override default table name (class name)
        self.columns = [
            Id("product_id"),
            Char("name", size=255).unique(),
            Integer("stock_quantity").default(0),
            Timestamp("added_on").useCurrent()
        ]

# Initialize and create
product_table = Product()
product_table.createTable()
```

### Column Types and Constraints

Fluent DB provides various column types:

*   `Id(column_name)`: Integer, Primary Key.
*   `Char(column_name, size=255)`: Fixed-length string.
*   `Varchar(column_name, size=255)`: Variable-length string.
*   `Text(column_name)`: Long text.
*   `LongText(column_name)`: Very long text.
*   `Integer(column_name, size=11)`: Integer.
*   `Decimal(column_name, size=11, decimal_places=2)`: Floating point number (uses `FLOAT` in SQLite).
*   `Boolean(column_name)`: Boolean (uses `TINYINT` in SQLite).
*   `Timestamp(column_name)`: Timestamp.

Common constraints (chainable methods on column types):

*   `.nullable()`: Allows NULL values.
*   `.default(value)`: Sets a default value.
*   `.unique()`: Ensures values in this column are unique.
*   `.primary()`: (For `Integer`) Marks as primary key.
*   `.auto_increment()`: (For `Integer`) Auto-increments value (SQLite typically does this for `INTEGER PRIMARY KEY`).
*   `.useCurrent()`: (For `Timestamp`) Sets default to `CURRENT_TIMESTAMP`.
*   `.useCurrentOnUpdate()`: (For `Timestamp`) Updates the timestamp automatically when the record is updated via the `update()` method.
*   `.regexp(pattern)`: (For `Char`, `Varchar`) Adds a `CHECK` constraint with a REGEXP (SQLite specific).

### DatabaseConnector

The `DatabaseConnector` class is an abstract base for database connections. `SQLiteConnector` is the concrete implementation for SQLite.

```python
from fluent_db import SQLiteConnector, Table # ... other imports

# Use a specific database file
connector = SQLiteConnector('my_application.db')

class MyModel(Table):
    def __init__(self):
        super().__init__(db_connector=connector) # Pass the shared connector
        self.columns = [Id("id")]

# Operations will use the 'my_application.db' file
MyModel().createTable()
```

### CRUD Operations

#### Create (`insert`)

```python
User().insert({"name": "Charlie", "age": 25})
```

#### Read (`get`, `first`)

```python
# Get all records
all_users = User().get()

# Get specific columns
user_names = User().get(["name", "age"])

# Get the first matching record
first_user = User().where("age", 30, operator=">").first()

# Get distinct values
distinct_ages = User().distinct("age").get(["age"])
```

#### Update (`update`)

```python
User().where("name", "Charlie").update({"age": 26})
```
*Note: `updated_at` (if defined with `.useCurrentOnUpdate()`) will be automatically updated.*

#### Delete (`delete`)

```python
User().where("age", 20, operator="<").delete()
```

### Querying and Filtering

#### `where(column, value, operator="=")`

```python
users_over_30 = User().where("age", 30, operator=">").get()
active_users = User().where("status", "active").get()
```

#### `orWhere(column, value, operator="=")`

```python
users_alice_or_bob = User().where("name", "Alice").orWhere("name", "Bob").get()
```

#### `whereIn(column, list_of_values)`

```python
selected_users = User().whereIn("id", [1, 5, 10]).get()
```

#### Nested Conditions (using a lambda)

```python
# SELECT * FROM User WHERE (age > 20 AND status = 'active') OR country = 'USA'
complex_query = User().where(lambda q: q.where("age", 20, ">").where("status", "active")) \
                      .orWhere("country", "USA") \
                      .get()
```

#### `order_by(column, order)`

`order` can be `'asc'` or `'desc'`.

```python
users_by_age_desc = User().order_by("age", "desc").get()
users_by_name_asc = User().order_by("name", "asc").order_by("age", "desc").get() # Multiple orders
```

#### `limit(count)`

```python
top_5_users = User().order_by("signup_date", "desc").limit(5).get()
```

#### `offset(count)`

Requires `limit()` to be set first.

```python
# Get users 6 through 10 (page 2 if page size is 5)
paged_users = User().order_by("id", "asc").limit(5).offset(5).get()
```

#### `distinct(column)`

Used to return only distinct (different) values for a specified column. Often used with `get([column_name])`.

```python
distinct_countries = User().distinct("country").get(["country"])
```

### Relationships

Fluent DB supports `hasOne` and `hasMany` relationships, allowing you to easily fetch related data by defining convenience methods in your table classes.

#### Defining Relationships

You define relationships by creating methods within your `Table` subclasses that call `self.hasMany()` or `self.hasOne()`. These methods should return the instance (`self`) to allow for further chaining.

Let's assume we have `User` and `Post` tables:

```python
from fluent_db import Table, Id, Char, Integer, Text, Timestamp, SQLiteConnector

# Shared connector for simplicity in this example
connector = SQLiteConnector('blog.db')

class User(Table):
    def __init__(self):
        super().__init__(db_connector=connector)
        self.columns = [
            Id("id"),
            Char("username").unique()
        ]

    # Define a method to fetch related posts
    def posts(self):
        # 'id' is the local key in User table
        # Post is the related table class
        # 'user_id' is the foreign key in the Post table
        return self.hasMany("id", [Post, "user_id"])

class Post(Table):
    def __init__(self):
        super().__init__(db_connector=connector)
        self.columns = [
            Id("id"),
            Integer("user_id"), # Foreign key to User.id
            Text("title"),
            Timestamp("created_at").useCurrent()
        ]

    # Define a method to fetch the related user
    def user(self):
        # 'user_id' is the local key in Post table (foreign key)
        # User is the related table class
        # 'id' is the foreign key in the User table (primary key of User)
        return self.hasOne("user_id", [User, "id"])

# Create tables (if they don't exist)
User().createTable()
Post().createTable()

# Insert sample data
if not User().where("username", "john_doe").first():
    User().insert({"username": "john_doe"})

# Fetch the user and check their posts
# When User().posts() is called, it sets up the relationship.
# The result will include a key 'Post' (the class name of the related table)
# containing a list of related post records.
john_with_posts_relation = User().posts().where("username", "john_doe").first()
# Expected output for john_with_posts_relation (if no posts yet):
# {'id': 1, 'username': 'john_doe', 'Post': []}
print(f"John with posts relation (initial): {john_with_posts_relation}")


# Insert posts for John if he has no posts
if john_with_posts_relation and 'Post' in john_with_posts_relation and not len(john_with_posts_relation['Post']) > 0:
    Post().insert({"user_id": john_with_posts_relation['id'], "title": "My First Post"})
    Post().insert({"user_id": john_with_posts_relation['id'], "title": "Another Post"})
    print("Inserted posts for John.")

```

#### Querying with Relationships

You query relationships by calling the methods you defined on your table instances.

```python
# Get user with their posts (hasMany)
print("\nFetching John with his posts:")
john_details = User().posts().where("username", "john_doe").first()

if john_details:
    print(f"User: {john_details['username']} (ID: {john_details['id']})")
    # Access related posts using the related table's class name as the key
    if "Post" in john_details and john_details["Post"]:
        print("  Posts:")
        for post_data in john_details["Post"]: # This will be a list of dicts
            print(f"    - Title: {post_data['title']} (ID: {post_data['id']})")
    else:
        print("  No posts found for this user.")
else:
    print("User 'john_doe' not found.")

# Example output for john_details:
# User: john_doe (ID: 1)
#   Posts:
#     - Title: My First Post (ID: 1)
#     - Title: Another Post (ID: 2)

# Get a post with its user (hasOne)
print("\nFetching the first post with its author:")
first_post_with_author = Post().user().first()

if first_post_with_author:
    print(f"Post Title: {first_post_with_author['title']} (ID: {first_post_with_author['id']})")
    # Access the related user using the related table's class name as the key
    if "User" in first_post_with_author and first_post_with_author["User"]:
        author_data = first_post_with_author["User"] # This will be a dict
        print(f"  Author: {author_data['username']} (ID: {author_data['id']})")
    else:
        print("  Author information not found for this post.")
else:
    print("No posts found.")

# Example output for first_post_with_author:
# Post Title: My First Post (ID: 1)
#   Author: john_doe (ID: 1)
```

**Note on Relationship Output Key:**

*   When you fetch data with relationships, the related records are included in the result dictionary.
*   The key for the related data defaults to the **class name of the related table** (e.g., `Post` for posts related to a `User`, or `User` for the user related to a `Post`).
*   If the main table being queried already has a column with the same name as the related table's class, the key for the related data will be prefixed with `relationWith_` (e.g., `relationWith_Post`) to avoid naming collisions.

**Note on Related Table Class Reference:**

In the examples above (`[Post, "user_id"]`), the related table class (`Post` or `User`) is passed directly. This works well in many cases. However, if you encounter **circular import dependencies** between your model files (e.g., `User` imports `Post` and `Post` imports `User`), you might need to pass the related table as a lambda function to defer its resolution:

```python
# In User class, if facing circular imports:
def posts(self):
    return self.hasMany("id", [lambda: Post, "user_id"])

# In Post class, if facing circular imports:
def user(self):
    return self.hasOne("user_id", [lambda: User, "id"])
```
This approach ensures the related class is looked up only when the relationship logic is actually executed, breaking the import cycle.

## Contributing

Contributions are welcome! Please feel free to submit pull requests, create issues for bugs, or suggest new features.

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## Future Enhancements (To-Do)

*   Support for other SQL databases (e.g., PostgreSQL, MySQL) by implementing new `DatabaseConnector` subclasses.
*   More complex relationship types (e.g., Many-to-Many).
*   Transaction management (`beginTransaction`, `commit`, `rollback`).
*   Database migration tools.
*   Enhanced data validation.
*   More comprehensive test suite.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
