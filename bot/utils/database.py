import json
import sqlite3
from typing import Any, Dict, Optional, Sequence, Union


class Database:
    def __init__(
            self,
            connection_path: Optional[str] = "./DataBase.db",
            *tables: Optional[str]

    ) -> None:
        """Initialize the Database object.

        Parameters:
        connection_path (Optional[str]): Path to the SQLite database file. Defaults to "./DataBase.db".
        *tables (Optional[str]): Table names to be created in the database if they do not exist.

        Returns:
        None
        """


        self._connection = sqlite3.Connection(
            connection_path
        )
        

        self._setup([*tables])


    
    def _setup(
            self,
            tables: Sequence[str] = ["main"]

    ) -> None:
        """Set up the tables in the database.

        Parameters:
        tables (Sequence[str]): List of table names to create. Defaults to ["main"].

        Returns:
        None
        """


        cur = self._connection.cursor()
        for table in tables:
            cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" (key UNIQUE, value)')
        
        self._connection.commit()


            

    def get(
            self,
            key: str,
            table: Optional[str] = "main"

    ) -> Union[None, Any]:
        """Retrieve a value from the database based on the key.

        Parameters:
        key (str): The key to search for in the table.
        table (Optional[str]): The table to query. Defaults to "main".

        Returns:
        Union[None, Any]: The value associated with the key, or None if the key does not exist.

        Raises:
        sqlite3.DatabaseError: If there is an error executing the query.
        """


        cur = self._connection.cursor()

        selected_value = [*cur.execute(f'SELECT value FROM "{table}" WHERE key = ?', (key,))]

        if selected_value != []:
            if len(selected_value[0]) > 0:

                return json.loads(selected_value[0][0])

        return None
                


    def set(
            self,
            key: str,
            value: Any,
            table: Optional[str] = "main"

    ) -> None:
        """Set a value in the database for a specific key.

        Parameters:
        key (str): The key to insert or update.
        value (Any): The value to be stored.
        table (Optional[str]): The table to update. Defaults to "main".

        Returns:
        None

        Raises:
        ValueError: If the value cannot be serialized to JSON.
        sqlite3.DatabaseError: If there is an error executing the query.
        """

        value = json.dumps(value)
        cur = self._connection.cursor()


        if self.get(key, table):
            cur.execute(f'UPDATE "{table}" SET value = ? WHERE key = ?', (value, key))
        else:
            cur.execute('INSERT INTO "{table}" (key, value) VALUES (?, ?)', (key, value))


        self._connection.commit()

        
    
    def delete(
            self,
            key: str,
            table: Optional[str] = "main"

    ) -> bool:
        """Delete a key-value pair from the database.

        Parameters:
        key (str): The key to delete.
        table (Optional[str]): The table to delete from. Defaults to "main".

        Returns:
        bool: True if the key was deleted successfully, False otherwise.

        Raises:
        sqlite3.DatabaseError: If there is an error executing the query.
        """


        old_value = self.get(
            key,
            table
        )

        cur = self._connection.cursor()
        cur.execute(f"DELETE FROM \"{table}\" WHERE key = ?", (key,))
        
        self._connection.commit()

        new_value = self.get(
            key,
            table
        )

        return old_value != new_value


    
    def push(
            self,
            key: str,
            value: Any,
            table: Optional[str] = "main"

    ) -> None:
        """Append a value to a list stored in the database.

        Parameters:
        key (str): The key to append the value to.
        value (Any): The value to append.
        table (Optional[str]): The table to update. Defaults to "main".

        Returns:
        None

        Raises:
        ValueError: If the existing value is not a list or is not empty.
        sqlite3.DatabaseError: If there is an error executing the query.
        """


        old_value = self.get(key, table)

        if old_value is not None:
            if not isinstance(old_value, Sequence):
                raise ValueError("Value in the database should be a list or empty to push and pull items")

            old_value.append(value)
            return self.set(
                key,
                old_value,
                table
            )



        value = [value]
        return self.set(
            key,
            value, 
            table
        )


    
    def pull(
            self,
            key: str,
            value: Any,
            table: Optional[str] = "main"

    ) -> None:
        """Remove a value from a list stored in the database.

        Parameters:
        key (str): The key to remove the value from.
        value (Any): The value to remove.
        table (Optional[str]): The table to update. Defaults to "main".

        Returns:
        None

        Raises:
        ValueError: If the existing value is not a list.
        sqlite3.DatabaseError: If there is an error executing the query.
        """

        old_value = self.get(
            key,
            value
        )
        if old_value is not None:


            if not isinstance(old_value, Sequence):
                raise ValueError("Value in the database should be a list or empty to push and pull items")

            if not value in old_value:
                return 
                        
            old_value.remove(value)


            return self.set(
                key,
                old_value,
                table
            )
    

    def sum(
            self,
            key: str,
            value: float,
            table: Optional[str] = "main"
            
    ) -> None:
        """Add a number to a stored value in the database.

        Parameters:
        key (str): The key to update.
        value (float): The number to add.
        table (Optional[str]): The table to update. Defaults to "main".

        Returns:
        None

        Raises:
        ValueError: If the value or the stored value is not a number.
        sqlite3.DatabaseError: If there is an error executing the query.
        """

        old_value = self.get(
            key,
            table
        )

        if not self._is_float(value):
            raise ValueError("The value should be an integer or float")

        if old_value is not None:

            if not self._is_float(old_value):
                raise ValueError("The old value should be an integer or float")

            new_value = old_value + value
            return self.set(
                key,
                new_value,
                table
            )
        

        return self.set(
            key,
            value,
            table
        )
     
    def sub(
            self,
            key: str,
            value: float,
            table: Optional[str] = "main"
            
    ) -> None:
        """Subtract a number from a stored value in the database.

        Parameters:
        key (str): The key to update.
        value (float): The number to subtract.
        table (Optional[str]): The table to update. Defaults to "main".

        Returns:
        None

        Raises:
        ValueError: If the value or the stored value is not a number.
        sqlite3.DatabaseError: If there is an error executing the query.
        """

        old_value = self.get(
            key,
            table
        )

        if not self._is_float(value):
            raise ValueError("The value should be an integer or float")

        if old_value is not None:

            if not self._is_float(old_value):
                raise ValueError("The old value should be an integer or float")

            new_value = old_value - value
            return self.set(
                key,
                new_value,
                table
            )
        

        return self.set(
            key,
            value,
            table
        )



    def values(
            self,
            table_name: str

    ) -> Sequence[Dict[str, Any]]:
        """Retrieve all key-value pairs from a table.

        Parameters:
        table_name (str): The name of the table to query.

        Returns:
        Sequence[Dict[str, Any]]: A list of dictionaries containing key-value pairs.

        Raises:
        sqlite3.DatabaseError: If there is an error executing the query.
        """


        cur = self._connection.cursor()

        cur.execute(f'SELECT * FROM {table_name}')
        values = [{row[0]: row[1]} for row in cur.fetchall()]
        
        return values


    def __enter__(
            self
    ) -> "Database":
        """Enter the runtime context related to this object.

        Returns:
        Database: The current instance of the class.
        """


        return self
    
    def __exit__(
            self,
            exc_type: Any, 
            exc_val: Any, 
            exc_tb: Any
    ) -> None:
        """Exit the runtime context related to this object.

        Parameters:
        exc_type (Any): The type of exception raised.
        exc_val (Any): The value of the exception raised.
        exc_tb (Any): The traceback object.

        Returns:
        None
        """

        self._connection.commit()
        self._connection.close()


    def _is_float(
            self,
            value: Any
    ) -> bool:
        """Check if a value can be converted to a float.

        Parameters:
        value (Any): The value to check.

        Returns:
        bool: True if the value can be converted to a float, False otherwise.
        """


        try:
            float(value)
            return True
        
        except ValueError:
            return False
    
