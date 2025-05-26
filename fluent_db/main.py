import datetime
import re
import warnings
import json
import sqlite3

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
        self.connection.close()
        self.cursor.close()

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

    # def disconnect(self):
    #     self._cursor.close()
    #     self._conn.close()

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
        self.database_connector.cursor.executescript(
            self.generate_insert_query(query, update=True))
        self.database_connector.connection.commit()
        for column in self.columns:
            if isinstance(column, Timestamp) and column.isCurrentOnUpdate:
                self.database_connector.cursor.executescript(
                    f"""UPDATE {self.table_name} SET {column.column_name} = {self.current_time}""")
        
        self.disconnect()

    def _runQuery(self, query: str):
        self.database_connector.cursor.executescript(query)
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
        self.database_connector.cursor.executescript(
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

        columns = ", ".join(col.create() for col in self.columns)
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
        self.isNullable = False


class Char(ColumnData):
    def __init__(self, column_name, size=255) -> None:
        super().__init__()
        self.column_name = column_name
        self._build = [column_name]
        self._build.append(f'CHAR({size})')

    def default(self, default_value='DEFAULT'):
        self._build.append(f"DEFAULT '{default_value}'")
        return self

    def unique(self):
        self._build.append("UNIQUE")
        return self

    def nullable(self):
        self._build.append("NULL")
        self.isNullable = True
        return self

    def regexp(self, regexp):
        if isinstance(regexp, re.Pattern):
            regexp = regexp.pattern
        self._build.append(f"CHECK (email REGEXP '{regexp}'")
        return self

    def create(self):
        return " ".join(self._build)


class Varchar(ColumnData):
    def __init__(self, column_name, size=255) -> None:
        super().__init__()
        self.column_name = column_name
        self._build = [column_name]
        self._build.append(f'VARCHAR({size})')

    def default(self, default_value='DEFAULT'):
        self._build.append(f"DEFAULT '{default_value}'")
        return self

    def unique(self):
        self._build.append("UNIQUE")
        return self

    def nullable(self):
        self._build.append("NULL")
        self.isNullable = True
        return self

    def regexp(self, regexp):
        if isinstance(regexp, re.Pattern):
            regexp = regexp.pattern
        self._build.append(f"CHECK (email REGEXP '{regexp}'")
        return self

    def create(self):
        return " ".join(self._build)


class Timestamp(ColumnData):

    def __init__(self, column_name) -> None:
        super().__init__()
        self.column_name = column_name
        self._build = [column_name]
        self._defalutPlaced = False
        self.isCurrentOnUpdate = False

    def default(self, default_value):
        if isinstance(default_value, datetime.datetime):
            default_value = default_value.strftime('%Y-%m-%d %H:%M:%S')

        if not self._defalutPlaced:
            self._defalutPlaced = True
            self._build.append(f"DEFAULT '{default_value}'")
        else:
            warnings.warn("Default values can not be more then one!")

        return self

    def useCurrent(self):
        if not self._defalutPlaced:
            self._defalutPlaced = True
            self._build.append(f"DEFAULT CURRENT_TIMESTAMP")
        else:
            warnings.warn("Default values can not be more then one!")
        return self

    def useCurrentOnUpdate(self):
        self.isCurrentOnUpdate = True
        return self

    def nullable(self):
        self._build.append("NULL")
        self.isNullable = True
        return self

    def create(self):
        return " ".join(self._build)


class Integer(ColumnData):
    def __init__(self, column_name, size=11) -> None:
        super().__init__()
        self.column_name = column_name
        self._build = [column_name]
        self._build.append(f'INT({size})')
        self.primary_key = False

    def auto_increment(self):
        self._build.append("AUTO_INCREMENT")
        return self

    def default(self, default_value):
        self._build.append(f"DEFAULT {default_value}")
        return self

    def unique(self):
        self._build.append("UNIQUE")
        return self

    def primary(self):
        self.primary_key = True
        return self

    def nullable(self):
        self._build.append("NULL")
        self.isNullable = True
        return self

    def create(self):
        if self.primary_key:
            self._build.append("PRIMARY KEY")
        return " ".join(self._build)


class Id(ColumnData):
    def __init__(self, column_name) -> None:
        super().__init__()
        self.column_name = column_name
        self.primary_key = True
        self._build = [column_name]
        self._build.append(f'INTEGER')

    def create(self):
        self._build.append("PRIMARY KEY")
        return " ".join(self._build)


class Decimal(ColumnData):
    def __init__(self, column_name, size=11, decimal_places=2):
        super().__init__()
        self.column_name = column_name
        self._build = [column_name]
        self._build.append(f'FLOAT({size},{decimal_places})')

    def default(self, default_value):
        self._build.append(f"DEFAULT {default_value}")
        return self

    def unique(self):
        self._build.append("UNIQUE")
        return self

    def nullable(self):
        self._build.append("NULL")
        self.isNullable = True
        return self

    def create(self):
        return " ".join(self._build)


class Boolean(ColumnData):
    def __init__(self, column_name):
        super().__init__()
        self.column_name = column_name
        self._build = [column_name]
        self._build.append('TINYINT')

    def default(self, default_value):
        if isinstance(default_value, bool):
            if default_value:
                default_value = 1
            else:
                default_value = 0
        else:
            if default_value > 1:
                default_value = 1
            elif (default_value < 0):
                default_value = 0
            else:
                default_value = int(default_value)

        self._build.append(f"DEFAULT {default_value}")
        return self

    def nullable(self):
        self._build.append("NULL")
        self.isNullable = True
        return self

    def create(self):
        return " ".join(self._build)


class Text(ColumnData):
    def __init__(self, column_name):
        super().__init__()
        self.column_name = column_name
        self._build = [column_name]
        self._build.append('TEXT')

    def default(self, default_value):
        self._build.append(f"DEFAULT '{default_value}'")
        return self

    def nullable(self):
        self._build.append("NULL")
        self.isNullable = True
        return self

    def create(self):
        return " ".join(self._build)


class LongText(ColumnData):
    def __init__(self, column_name):
        super().__init__()
        self.column_name = column_name
        self._build = [column_name]
        self._build.append('LONGTEXT')

    def default(self, default_value):
        self._build.append(f"DEFAULT '{default_value}'")
        return self

    def nullable(self):
        self._build.append("NULL")
        self.isNullable = True
        return self

    def create(self):
        return " ".join(self._build)
