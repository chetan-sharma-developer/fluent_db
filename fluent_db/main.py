import datetime
import re
import warnings
import json
import sqlite3
import os
import subprocess
import mysql.connector
from mysql.connector import Error

class DatabaseConnector():
    def __init__(self):
        self.db_type = None

class SQLiteConnector(DatabaseConnector):
    def __init__(self, db_path):
        self.db_type = "sqlite"
        self.database_path = db_path
        self.connection = sqlite3.connect(self.database_path)
        self.cursor = self.connection.cursor()

    def disconnect(self):
        try:
            self.connection.close()
            self.cursor.close()
        except:
            pass

class MySQLConnector(DatabaseConnector):
    def __init__(self, port: int = 3306, host: str = "127.0.0.1",
                 user: str = "root", password: str = "", dbname=None, standalone: bool = False, datadir: str = None):
        self.db_type = "mysql"
        self.connection = None
        self.cursor = None
        if (dbname is None):
            raise ValueError("Database name is required for MySQL connection.")
        
        if standalone:
            self.sql_bin_folder:str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")

            if datadir is not None:
                self.data_dir = datadir
            else:
                self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)

            required_files = ["ibdata1", "auto.cnf"]
            is_initialized = all([os.path.exists(os.path.join(self.data_dir, f)) for f in required_files])

            if not is_initialized:
                os.system(f'{os.path.join(self.sql_bin_folder, "mysql_install_db")} --datadir="{self.data_dir}" --password="{password}" --default-user')

            subprocess.Popen([
                os.path.join(self.sql_bin_folder, "mysqld"),
                "--port=3306",
                f"--basedir={self.sql_bin_folder}",
                f"--datadir={self.data_dir}",
                "--standalone"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            self.connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                port=port
            )
            self.cursor = self.connection.cursor()
        except Error as e:
            raise ConnectionError(f"Error connecting to MySQL server: {e}")
        
        if not self.connection.is_connected():
            raise ConnectionError(f"Error connecting to MySQL server.")
        
        self.select_db(dbname)
            

    def select_db(self, dbname: str):
        if dbname is None:
            return

        if not self.connection.is_connected():
            raise ConnectionError("Not connected to MySQL server.")

        cursor = self.connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {dbname}")
        cursor.execute(f"USE {dbname}")
        self.connection.commit()
        cursor.close()

class Table:
    def __init__(self, db_connector:DatabaseConnector=SQLiteConnector('database.db')) -> None:
        self.table_name = self.__class__.__name__
        self.columns = []
        self.current_time = "CURRENT_TIMESTAMP"
        self._conditions = []
        self.database_connector:DatabaseConnector = db_connector
        self._limit = False
        self.__hasPrimary = [
            Id, Integer
        ]
        self._offset = False
        self._order_by = []
        self._distinct = False
        self._relation = []

    def disconnect(self):
        self.database_connector.disconnect()

    def hasOne(self, main_column: str, belongs_to: list):
        """
        Establishes a one-to-one relationship between the main column and the specified columns.

        Args:
            main_column (str): The name of the main column.
            belongs_to (list): A list containing two elements. The first element is a callable that returns the related table,
                               and the second element is the related column name.

        Returns:
            self: Returns the instance of the class to allow method chaining.
        """
        self._relation.append([main_column, [belongs_to[0](), belongs_to[1]], "one", self.getPrimaryColumn(belongs_to[0]())])
        return self

    def hasMany(self, main_column: str, belongs_to: list):
        """
        Establishes a "has many" relationship between the main column and the related columns.

        Args:
            main_column (str): The name of the main column that has the relationship.
            belongs_to (list): A list containing two elements:
                - The first element is a callable that returns the related model.
                - The second element is the related column name.

        Returns:
            self: The instance of the class to allow method chaining.
        """
        self._relation.append([main_column, [belongs_to[0](), belongs_to[1]], "many", self.getPrimaryColumn(belongs_to[0]())])
        return self

    def where(self, column, value=None, operator="="):
        """
        Adds a condition to the query based on the specified column and value.
        Parameters:
        column (str or callable): The column name to apply the condition on, or a callable that builds a condition.
        value (any, optional): The value to compare the column against. Required if column is a string.
        operator (str, optional): The comparison operator to use. Defaults to "=".
        Returns:
        self: The instance of the class to allow for method chaining.
        Raises:
        ValueError: If value is None and column is not callable.
        """

        if not callable(column):
            # If the column is not a callable, add a condition based on the column and value
            if value is None:
                raise ValueError("Value is required!")
            if len(self._conditions) == 0:
                self._conditions.append(
                    f"""{self.table_name}.{column} {operator} {self._defineType(value)}""")
            else:
                self._conditions.append(
                    f"""AND {self.table_name}.{column} {operator} {self._defineType(value)}""")
            return self

        # If the column is a callable, build a nested condition
        condition_builder = ConditionBuilder(self.table_name)
        column(condition_builder)
        condition = condition_builder.build()

        if len(self._conditions) == 0:
            self._conditions.append(f"({condition})")
        else:
            self._conditions.append(f'AND ({condition})')

        return self

    def whereIn(self, column, value: list):
        """
        Adds a condition to the query to filter rows where the specified column's value is in the provided list.
        Args:
            column (str): The name of the column to filter.
            value (list): A list of values to filter the column by.
        Raises:
            ValueError: If the provided value is not a list, is None, or is an empty list.
        Returns:
            self: The instance of the class to allow method chaining.
        """
        if (not isinstance(value, list)) or value is None or len(value) == 0:
            raise ValueError("Value is required!")

        if len(self._conditions) == 0:
            self._conditions.append(
                f"""{self.table_name}.{column} IN ({', '.join([self._defineType(val) for val in value])})""")
        else:
            self._conditions.append(
                f"""AND {self.table_name}.{column} IN ({', '.join([self._defineType(val) for val in value])})""")
        return self
    
    def order_by(self, column:str, order:str):
        """
        Adds an order by clause to the query.
        Args:
            column (str): The name of the column to order by.
            order (str): The order direction, either 'asc' for ascending or 'desc' for descending.
        Raises:
            ValueError: If the order is not 'asc' or 'desc'.
        Returns:
            self: The instance of the query with the added order by clause.
        """
        if order.lower() not in ['asc', 'desc']:
            raise ValueError("Order must be 'asc' or 'desc'")

        self._order_by.append({
            'column': column,
            'order': order.upper()
        })
        return self

    def orWhere(self, column, value, operator="="):
        """
        Adds an OR condition to the query's WHERE clause.
        Parameters:
        column (str or callable): The column name to apply the condition on, or a callable that builds a nested condition.
        value (any): The value to compare the column against.
        operator (str, optional): The comparison operator to use. Defaults to "=".
        Returns:
        self: The instance of the query builder with the added condition.
        """
        if not callable(column):
            if len(self._conditions) == 0:
                self._conditions.append(
                    f"""{self.table_name}.{column} {operator} {self._defineType(value)}""")
            else:
                self._conditions.append(
                    f"""OR {self.table_name}.{column} {operator} {self._defineType(value)}""")

        else:
            condition_builder = ConditionBuilder(self.table_name)
            column(condition_builder)
            condition = condition_builder.build()

            if len(self._conditions) != 0:
                self._conditions.append(condition)
            else:
                self._conditions.append(f'OR ({condition})')

        return self

    def distinct(self, column: str):
        """
        Sets the column to be used for distinct selection.

        Args:
            column (str): The name of the column to apply distinct selection on.

        Returns:
            self: Returns the instance of the class to allow method chaining.
        """
        self._distinct = column
        return self

    def update(self, query: dict):
        """
        Updates the table with the provided query.
        This method connects to the database, executes the provided query to update the table,
        commits the changes, and updates any columns that are instances of `Timestamp` and have
        `isCurrentOnUpdate` set to True with the current time.
        Args:
            query (dict): A dictionary representing the query to be executed.
        Raises:
            Exception: If there is an error connecting to the database or executing the query.
        """
        self.database_connector.cursor.execute(
            self.generate_insert_query(query, update=True))
        self.database_connector.connection.commit()
        for column in self.columns:
            if isinstance(column, Timestamp) and column.isCurrentOnUpdate:
                self.database_connector.cursor.execute(
                    f"""UPDATE {self.table_name} SET {column.column_name} = {self.current_time}""")
        
        # self.disconnect()

    def _runQuery(self, query: str):
        self.database_connector.cursor.execute(query)
        self.database_connector.connection.commit()
        # self.disconnect()

    def insert(self, query: dict):
        """
        Inserts a new record into the database.

        Args:
            query (dict): A dictionary containing the data to be inserted.

        Raises:
            sqlite3.DatabaseError: If an error occurs while executing the SQL script.

        """
        # self.connect()
        self.database_connector.cursor.execute(
            self.generate_insert_query(query, update=False))
        self.database_connector.connection.commit()
        # self.disconnect()

    def _valueStringHandler(self, value):
        if isinstance(value, str):
            if '"' in value and "'" in value:
                value = value.replace('"', '\"')
                return f'"{value}"'
            elif '"' in value:
                return f"'{value}'"
            else:
                return f'"{value}"'
        elif isinstance(value, datetime.datetime):
            return f'"{value.strftime(r"%Y-%m-%d %H:%M:%S")}"'
        elif isinstance(value, dict):
            return f"'{json.dumps(value)}'"
        else:
            return str(value)

    def generate_insert_query(self, data_dict: dict, update: bool):
        """
        Generates an SQL insert or update query based on the provided data dictionary.
        Args:
            data_dict (dict): A dictionary containing column-value pairs to be inserted or updated.
            update (bool): A flag indicating whether to generate an update query (True) or an insert query (False).
        Returns:
            str: The generated SQL query string.
        """
        columns = ', '.join(data_dict.keys())
        values_array = [self._valueStringHandler(val) for val in data_dict.values()]
        values = ', '.join(values_array)

        if not update:
            query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({values})"
        else:
            temp_array = ', '.join(f"{val[0]} = {val[1]}" for val in zip(
                data_dict.keys(), values_array))
            query = f"UPDATE {self.table_name} SET {temp_array}"+(
                f" WHERE {self._buildCondition()}" if len(self._conditions) != 0 else '')
        
        return query

    def offset(self, offset: int):
        """
        Sets the offset for the query.

        Parameters:
        offset (int): The number of rows to skip before starting to return rows.

        Returns:
        self: The instance of the class to allow method chaining.

        Raises:
        ValueError: If the limit is not set before setting the offset.
        """
        if not self._limit:
            raise ValueError("limit is required to be there before offset!")
        self._offset = offset
        return self

    def limit(self, limit: int):
        """
        Set a limit for the number of items.

        Parameters:
        limit (int): The maximum number of items to be set. Must be a valid integer.

        Returns:
        self: Returns the instance of the class to allow for method chaining.

        Raises:
        ValueError: If the provided limit is not an integer.
        """
        if (not isinstance(limit, int)):
            raise ValueError("Limit value should be valid 'int'!")
        self._limit = limit
        return self

    def _buildCondition(self):
        return ' '.join(self._conditions)

    def _buildHead(self, select):
        select = self._buildSelection(select)
        if len(self._relation) != 0:
            relationQuery = ""
            for relate in self._relation:
                withCurrent, [relationTable, relateId], relationType, _ = relate
                relationTable = relationTable.table_name
                relationQuery+=f""" LEFT JOIN {relationTable} ON {self.table_name}.{withCurrent} = {relationTable}.{relateId}"""
        
        return f"""SELECT {select} FROM `{self.table_name}`"""+(relationQuery if len(self._relation) != 0 else "")

    def _buildSelection(self, select):
        if len(select) == 0:
            if len(self._relation) == 0:
                return "*"
            select = f"`{self.table_name}`.*"
            for relate in self._relation:
                table_name = relate[1][0].table_name
                relateWith = relate[3]
                relation_type = relate[2]
                select+=f""", "divider_for_{relation_type}_{relateWith}_{table_name}", `{table_name}`.*"""
        else:
            select = " ,".join(select)

        return select


    def _buildTail(self):
        COLUMN_TEXT = "column"
        ORDER_TEXT = "order"

        return f"""{f" GROUP BY {self._distinct}" if self._distinct else ''}{f" ORDER BY {', '.join([f'{order[COLUMN_TEXT]} {order[ORDER_TEXT]}' for order in self._order_by])}" if len(self._order_by) != 0 else ''}{f" LIMIT {self._limit}" if self._limit else ''}{f" OFFSET {self._offset}" if self._offset else ''}"""

    def get(self, columns=None):
        """
        Retrieve data from the table based on specified columns.
        Args:
            columns (str or list, optional): The column(s) to be selected. 
                If a string is provided, it will be converted to a list with one element.
                If None is provided, an empty list will be used.
                If not a string or list, a ValueError will be raised.
        Returns:
            parent: The result of the executed query based on the specified columns and conditions.
        Raises:
            ValueError: If the columns argument is not a string, list, or None.
        """
        if isinstance(columns, str):
            columns = [columns]
        elif columns is None:
            columns = []
        elif not isinstance(columns, list):
            raise ValueError("Not able to identify column!")

        toBeSelected = columns
        parent = self._excecuteQuery(self._buildHead(
            toBeSelected)+f"""{f" WHERE {self._buildCondition()}" if len(self._conditions) != 0 else ''}"""+self._buildTail())

        return parent

    def delete(self):
        """
        Deletes records from the table based on the specified conditions.

        This method constructs and executes a DELETE SQL query to remove records
        from the table. If conditions are specified, they are included in the
        WHERE clause of the query.

        Returns:
            None
        """
        
        self._runQuery(f""" DELETE FROM {self.table_name}{f" WHERE {self._buildCondition()}" if len(self._conditions) != 0 else ''}""")
        return None

    def first(self, columns=None):
        """
        Retrieve the first row from the table based on the specified columns and conditions.
        Args:
            columns (str or list, optional): The column(s) to be selected. If a string is provided, it will be converted to a list. 
                                              If None, an empty list will be used. Defaults to None.
        Returns:
            dict or None: The first row of the result as a dictionary if available, otherwise None.
        Raises:
            ValueError: If the columns argument is not a string, list, or None.
        """
        if isinstance(columns, str):
            columns = [columns]
        elif columns is None:
            columns = []
        elif not isinstance(columns, list):
            raise ValueError("Not able to identify column!")

        self._limit = 1
        self._offset = False
        toBeSelected = columns
        result = self._excecuteQuery(self._buildHead(toBeSelected)+f"""{f" WHERE {self._buildCondition()}" if len(self._conditions) != 0 else ''}"""+self._buildTail())
        return result[0] if len(result)!=0 else None

    def _defineType(self, val):
        return (f'"{val}"' if isinstance(val, str) else (f'"{val.strftime(r"%Y-%m-%d %H:%M:%S")}"' if isinstance(val, datetime.datetime) else str(val)))

    def getPrimaryColumn(self, table=None):
        """
        Retrieves the name of the primary key column from the table.
        Args:
            table (Table, optional): An optional Table object to search for the primary key column. 
                                     If not provided, the method will use the columns of the current instance.
        Returns:
            str: The name of the primary key column.
        Raises:
            ValueError: If no primary key column is found in the specified table or the current instance.
        """
        columns = self.columns
        
        if table is not None and isinstance(table, Table):
            columns = table.columns

        for column in columns:
            for prime in self.__hasPrimary:
                if isinstance(column, prime) and column.primary_key:
                    return column.column_name
        
        raise ValueError(f"Did not found primary key in {self.table_name if table is None else table.table_name} table! Please define it in columns list.")

    def _excecuteQuery(self, query, named_key=True):
        # self.connect()
        self.database_connector.cursor.execute(query)

        if named_key:
            if len(self._relation) == 0:
                columns = [col[0] for col in self.database_connector.cursor.description]
                results = self.database_connector.cursor.fetchall()
                results = [dict(zip(columns, row)) for row in results]

            else:
                results = self.database_connector.cursor.fetchall()
                new_result = []
                columns = [col[0] for col in self.database_connector.cursor.description]
                primary_column = {}
                primary_column[self.table_name] = self.getPrimaryColumn()

                for rp in self._relation:
                    primary_column[rp[1][0].table_name] = rp[-1]

                lastRowId = {}
                manyRecords = {}
                record = {}
                changedRelation = True
                listOfMany = []
                for row in results:
                    record = {}
                    currentSaving = self.table_name
                    skipColumn = False
                    relationType = "one"
                    for c, r in zip(columns, row):

                        if currentSaving not in lastRowId:
                            lastRowId[currentSaving] = None

                        if currentSaving == self.table_name and c == primary_column[currentSaving] and lastRowId[currentSaving] != r:
                            changedRelation = True
                            manyRecords = {}

                        if relationType == "one" and c == primary_column[currentSaving]:

                            if lastRowId[currentSaving] == r:
                                skipColumn = True
                            else:
                                lastRowId[currentSaving] = r
                                
                        elif relationType == "many" and c == primary_column[currentSaving]:

                            if currentSaving not in manyRecords:
                                manyRecords[currentSaving] = []

                            if lastRowId[currentSaving] == r:
                                skipColumn = True

                            lastRowId[currentSaving] = r


                        if currentSaving not in record:
                            record[currentSaving] = []
                        
                        if c.startswith('"divider_for_') and r.startswith('divider_for_'):
                            if len(record[currentSaving]) != 0:
                                record_dict = dict(record[currentSaving])
                                if relationType == 'many' and record_dict[primary_column[currentSaving]] is not None:
                                    if currentSaving not in listOfMany:
                                        listOfMany.append(currentSaving)


                                    if currentSaving != listOfMany[-1] or len(primary_column.keys()) == 2:
                                        manyRecords[currentSaving].append(record_dict)

                                    elif record_dict[primary_column[currentSaving]] not in [keep[primary_column[currentSaving]] for keep in manyRecords[currentSaving]]:
                                        manyRecords[currentSaving].append(record_dict)
                                        

                            relationType, _, new_relation = r.replace("divider_for_", "").split("_", 2)
                            skipColumn = False
                                
                            currentSaving = new_relation

                        else:
                            if not skipColumn:
                                record[currentSaving].append([c, r])                  

                    for key in record.keys():
                        record[key] = dict(record[key])

                    if relationType == 'many' and primary_column[currentSaving] in record[currentSaving] and record[currentSaving][primary_column[currentSaving]] is not None:
                        if len(primary_column.keys()) == 2:
                            manyRecords[currentSaving].append(record[currentSaving])

                        elif record[currentSaving][primary_column[currentSaving]] not in [keep[primary_column[currentSaving]] for keep in manyRecords[currentSaving]]:
                            manyRecords[currentSaving].append(record[currentSaving])
                            if currentSaving not in listOfMany:
                                listOfMany.append(currentSaving)

                    new_record = record[self.table_name]
                    del record[self.table_name]

                    for i in manyRecords.keys():
                        record[i] = manyRecords[i]

                    for i in record.keys():
                        if i in new_record:
                            new_record['relationWith_'+i] = record[i]
                        else:
                            new_record[i] = record[i]

                        
                    if changedRelation:
                        changedRelation = False
                        new_result.append(new_record)


                results = new_result

        else:
            results = self.database_connector.cursor.fetchall()

        return results

    def createTable(self):
        """
        Creates a SQL table based on the columns defined in the instance.
        This method constructs a SQL `CREATE TABLE` query using the columns
        provided in the instance. It ensures that all columns are of type
        `ColumnData` before creating the table. If any column is not of the
        required type, a `ValueError` is raised.
        Returns:
            str: The SQL query string used to create the table.
        Raises:
            ValueError: If any column is not an instance of `ColumnData`.
        """
        for column in self.columns:
            if not isinstance(column, ColumnData):
                raise ValueError(
                    'All columns are required to be type of ColumnData!')

        columns = ", ".join(col.create(self.database_connector.db_type) for col in self.columns)
        query = f'''CREATE TABLE IF NOT EXISTS {self.table_name} ({columns})'''
        self._runQuery(query)
        return query

class ConditionBuilder:
    def __init__(self, table_name):
        self._table_name = table_name
        self._conditions = []

    def where(self, column, value, operator="="):
        if len(self._conditions) == 0:
            self._conditions.append(
                f"""{self._table_name}.{column} {operator} {self._defineType(value)}""")
        else:
            self._conditions.append(
                f"""AND {self._table_name}.{column} {operator} {self._defineType(value)}""")
        return self
    
    def whereIn(self, column, value: list):
        if (not isinstance(value, list)) or value is None or len(value) == 0:
            raise ValueError("Value is required!")

        if len(self._conditions) == 0:
            self._conditions.append(
                f"""{self._table_name}.{column} IN ({', '.join([self._defineType(val) for val in value])})""")
        else:
            self._conditions.append(
                f"""AND {self._table_name}.{column} IN ({', '.join([self._defineType(val) for val in value])})""")
        return self


    def orWhere(self, column, value, operator="="):
        self._conditions.append(
            f'OR {self._table_name}.{column} {operator} {self._defineType(value)}')
        return self

    def _defineType(self, val):
        return (f'"{val}"' if isinstance(val, str) else (f'"{val.strftime(r"%Y-%m-%d %H:%M:%S")}"' if isinstance(val, datetime.datetime) else str(val)))

    def build(self):
        return ' '.join(self._conditions)


class ColumnData:
    def __init__(self) -> None:
        self.isNullable: bool = False # By default, columns are NOT NULL unless nullable() is called
        self._constraints: list[str] = [] # For DEFAULT, UNIQUE, CHECK etc.

    def _add_common_constraints(self, parts: list[str], db_type: str) -> None:
        """Helper to add NOT NULL/NULL and other constraints."""
        # Determine if this column is effectively a Primary Key for NOT NULL logic
        is_pk_effectively = False
        if isinstance(self, Id):
            is_pk_effectively = True
        elif hasattr(self, 'primary_key') and getattr(self, 'primary_key'):
            is_pk_effectively = True
        
        # Nullability
        if self.isNullable:
            parts.append("NULL")
        else:
            # PKs are implicitly NOT NULL in SQLite.
            # For MySQL, explicit NOT NULL is good even for PKs.
            if db_type == 'sqlite' and is_pk_effectively:
                pass  # SQLite PK is implicitly NOT NULL
            else:
                parts.append("NOT NULL")
        
        parts.extend(self._constraints)


class Char(ColumnData):
    def __init__(self, column_name: str, size: int = 255) -> None:
        super().__init__()
        self.column_name: str = column_name
        self.size: int = size

    def default(self, default_value: str = 'DEFAULT'): # Note: 'DEFAULT' keyword not valid SQL string literal
        self._constraints.append(f"DEFAULT '{default_value}'")
        return self

    def unique(self):
        self._constraints.append("UNIQUE")
        return self

    def nullable(self):
        self.isNullable = True
        return self

    def regexp(self, regexp_pattern: re.Pattern):
        if isinstance(regexp_pattern, re.Pattern):
            regexp_pattern = regexp_pattern.pattern
        # Ensure single quotes in pattern are escaped for SQL
        escaped_regexp = regexp_pattern.replace("'", "''")
        self._constraints.append(f"CHECK ({self.column_name} REGEXP '{escaped_regexp}')")
        return self

    def create(self, db_type: str = 'sqlite') -> str:
        parts = [self.column_name]
        parts.append(f'CHAR({self.size})') # Same for SQLite and MySQL
        
        self._add_common_constraints(parts, db_type)
        return " ".join(parts)


class Varchar(ColumnData):
    def __init__(self, column_name: str, size: int = 255) -> None:
        super().__init__()
        self.column_name: str = column_name
        self.size: int = size

    def default(self, default_value: str = 'DEFAULT'): # Note: 'DEFAULT' keyword not valid SQL string literal
        self._constraints.append(f"DEFAULT '{default_value}'")
        return self

    def unique(self):
        self._constraints.append("UNIQUE")
        return self

    def nullable(self):
        self.isNullable = True
        return self

    def regexp(self, regexp_pattern: re.Pattern):
        if isinstance(regexp_pattern, re.Pattern):
            regexp_pattern = regexp_pattern.pattern
        escaped_regexp = regexp_pattern.replace("'", "''")
        self._constraints.append(f"CHECK ({self.column_name} REGEXP '{escaped_regexp}')")
        return self

    def create(self, db_type: str = 'sqlite') -> str:
        parts = [self.column_name]
        parts.append(f'VARCHAR({self.size})') # Same for SQLite and MySQL
        
        self._add_common_constraints(parts, db_type)
        return " ".join(parts)


class Timestamp(ColumnData):
    def __init__(self, column_name: str) -> None:
        super().__init__()
        self.column_name: str = column_name
        self._default_placed: bool = False
        self.isCurrentOnUpdate: bool = False

    def default(self, default_value: datetime.datetime):
        if self._default_placed:
            warnings.warn("Default value has already been set for this Timestamp column.", UserWarning)
            return self
            
        if isinstance(default_value, datetime.datetime):
            default_value = default_value.strftime('%Y-%m-%d %H:%M:%S')
        
        self._constraints.append(f"DEFAULT '{default_value}'")
        self._default_placed = True
        return self

    def useCurrent(self):
        if self._default_placed:
            warnings.warn("Default value has already been set for this Timestamp column.", UserWarning)
            return self
        self._constraints.append(f"DEFAULT CURRENT_TIMESTAMP")
        self._default_placed = True
        return self

    def useCurrentOnUpdate(self):
        self.isCurrentOnUpdate = True
        return self

    def nullable(self):
        self.isNullable = True
        return self

    def create(self, db_type: str = 'sqlite') -> str:
        parts = [self.column_name]
        if db_type == 'mysql':
            parts.append('TIMESTAMP')
        else: # sqlite
            parts.append('DATETIME') # SQLite uses DATETIME more commonly for this behavior

        self._add_common_constraints(parts, db_type) # Handles NULL/NOT NULL and existing constraints

        if db_type == 'mysql' and self.isCurrentOnUpdate:
            parts.append('ON UPDATE CURRENT_TIMESTAMP')
            
        return " ".join(parts)


class Integer(ColumnData):
    def __init__(self, column_name: str, size: int = 11) -> None:
        super().__init__()
        self.column_name: str = column_name
        self.size: int = size # Mainly for MySQL display width
        self.is_auto_increment: bool = False
        self.primary_key: bool = False

    def auto_increment(self):
        self.is_auto_increment = True
        # For SQLite, auto_increment implies PRIMARY KEY on an INTEGER column
        if not self.primary_key:
            self.primary_key = True 
        return self

    def default(self, default_value: int):
        self._constraints.append(f"DEFAULT {default_value}")
        return self

    def unique(self):
        if self.primary_key:
             warnings.warn(f"Column '{self.column_name}' is already a PRIMARY KEY, which implies UNIQUE. Explicit UNIQUE constraint skipped.", UserWarning)
        else:
            self._constraints.append("UNIQUE")
        return self

    def primary(self):
        self.primary_key = True
        return self

    def nullable(self):
        if self.primary_key:
            warnings.warn(f"PRIMARY KEY column '{self.column_name}' cannot be NULL. nullable() call ignored.", UserWarning)
        else:
            self.isNullable = True
        return self

    def create(self, db_type: str = 'sqlite') -> str:
        parts = [self.column_name]

        if db_type == 'mysql':
            parts.append(f'INT({self.size})')
            # Nullability for MySQL (PK implies NOT NULL, but explicit is fine)
            if self.primary_key:
                self.isNullable = False # Force NOT NULL for PK
            
            self._add_common_constraints(parts, db_type)

            if self.is_auto_increment:
                parts.append("AUTO_INCREMENT")
            if self.primary_key and "PRIMARY KEY" not in parts : # Check if already added by _add_common_constraints somehow
                # Find a suitable place or just append
                pk_idx = -1
                for i, p in enumerate(parts):
                    if p.upper() == "AUTO_INCREMENT" or p.upper().startswith("DEFAULT") or p.upper() == "UNIQUE":
                        pk_idx = i + 1
                        break
                if pk_idx != -1 and pk_idx < len(parts):
                     parts.insert(pk_idx, "PRIMARY KEY")
                else:
                     parts.append("PRIMARY KEY")


        else: # sqlite
            parts.append('INTEGER')
            # For SQLite, an INTEGER PRIMARY KEY is implicitly an alias for ROWID and auto-incrementing.
            # If auto_increment is true, it MUST be INTEGER PRIMARY KEY AUTOINCREMENT for specific behavior.
            
            # Handle PK and AUTOINCREMENT together for SQLite
            pk_added = False
            if self.primary_key:
                if self.is_auto_increment:
                    parts.append("PRIMARY KEY AUTOINCREMENT")
                    self.isNullable = False # PK implies NOT NULL
                else:
                    parts.append("PRIMARY KEY")
                    self.isNullable = False # PK implies NOT NULL
                pk_added = True
            
            self._add_common_constraints(parts, db_type)
            
            # If unique was called on a PK, SQLite would raise an error if "UNIQUE" is added again.
            # _add_common_constraints might add "UNIQUE". We need to ensure it's not redundant.
            if pk_added and "UNIQUE" in parts:
                parts.remove("UNIQUE") # PK implies UNIQUE

        return " ".join(parts)


class Id(ColumnData):
    def __init__(self, column_name: str = 'id') -> None: # Default column name to 'id'
        super().__init__()
        self.column_name: str = column_name
        self.isNullable = False # IDs are never nullable
        self.primary_key = True # IDs are always primary keys

    def create(self, db_type: str = 'sqlite') -> str:
        parts = [self.column_name]
        if db_type == 'mysql':
            parts.extend(['INT', 'NOT NULL', 'AUTO_INCREMENT', 'PRIMARY KEY'])
        else: # sqlite
            # INTEGER PRIMARY KEY AUTOINCREMENT is the standard way for auto-incrementing IDs
            parts.extend(['INTEGER', 'NOT NULL', 'PRIMARY KEY', 'AUTOINCREMENT'])
        # No need to call _add_common_constraints as everything is explicit here
        return " ".join(parts)


class Decimal(ColumnData): # Changed from Float to Decimal for precision
    def __init__(self, column_name: str, precision: int = 10, scale: int = 2): # Use precision and scale
        super().__init__()
        self.column_name: str = column_name
        self.precision: int = precision
        self.scale: int = scale

    def default(self, default_value: float):
        self._constraints.append(f"DEFAULT {default_value}")
        return self

    def unique(self):
        self._constraints.append("UNIQUE")
        return self

    def nullable(self):
        self.isNullable = True
        return self

    def create(self, db_type: str = 'sqlite') -> str:
        parts = [self.column_name]
        if db_type == 'mysql':
            parts.append(f'DECIMAL({self.precision},{self.scale})')
        else: # sqlite
            # SQLite uses NUMERIC. It can store any precision, but this helps define affinity.
            parts.append(f'NUMERIC({self.precision},{self.scale})')
        
        self._add_common_constraints(parts, db_type)
        return " ".join(parts)

class Boolean(ColumnData):
    def __init__(self, column_name: str):
        super().__init__()
        self.column_name: str = column_name

    def default(self, default_value: bool):
        sql_val = 0
        if isinstance(default_value, bool):
            sql_val = 1 if default_value else 0
        else: # int
            sql_val = 1 if int(default_value) > 0 else 0
        self._constraints.append(f"DEFAULT {sql_val}")
        return self

    def nullable(self):
        self.isNullable = True
        return self

    def create(self, db_type: str = 'sqlite') -> str:
        parts = [self.column_name]
        if db_type == 'mysql':
            parts.append('TINYINT(1)') # Common practice for boolean in MySQL
        else: # sqlite
            parts.append('INTEGER') # SQLite recommends INTEGER for booleans (0 or 1)
        
        self._add_common_constraints(parts, db_type)
        return " ".join(parts)


class Text(ColumnData):
    def __init__(self, column_name: str):
        super().__init__()
        self.column_name: str = column_name

    def default(self, default_value: str):
        self._constraints.append(f"DEFAULT '{default_value}'")
        return self

    def nullable(self):
        self.isNullable = True
        return self

    def create(self, db_type: str = 'sqlite') -> str:
        parts = [self.column_name, 'TEXT'] # TEXT is common for both
        self._add_common_constraints(parts, db_type)
        return " ".join(parts)


class LongText(ColumnData):
    def __init__(self, column_name: str):
        super().__init__()
        self.column_name: str = column_name

    def default(self, default_value: str):
        self._constraints.append(f"DEFAULT '{default_value}'")
        return self

    def nullable(self):
        self.isNullable = True
        return self

    def create(self, db_type: str = 'sqlite') -> str:
        parts = [self.column_name]
        if db_type == 'mysql':
            parts.append('LONGTEXT')
        else: # sqlite
            parts.append('TEXT') # SQLite doesn't have a distinct LONGTEXT
        
        self._add_common_constraints(parts, db_type)
        return " ".join(parts)