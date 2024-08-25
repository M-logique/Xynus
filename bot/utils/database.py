import json
from typing import Any, Dict, Sequence, Union

from asyncpg import Connection


class KVDatabase:
    def __init__(
            self,
            connection: Connection,
            /

    ) -> None:
        """Initialize the KVDatabase object.

        Parameters:
        connection (asyncpg.Connection): The database connection object.

        Returns:
        None
        """


        self._connection = connection
        


    async def get(
            self, 
            key: str, 
            
    ) -> Union[None, Any]:
        """Retrieve a value from the database using a hierarchical key.

        Parameters:
        key (str): The hierarchical key to search for, which may include nested levels separated by dots.

        Returns:
        Union[None, Any]: The value associated with the key, or None if the key does not exist.

        Raises:
        asyncpg.PostgresError: If there is an error executing the query.
        """
        keys = key.split('.')
        root_key = keys[0]
        root_value = await self._get(root_key)
        if root_value is None:
            return None
        try:
            return self._traverse_dict(root_value, keys[1:])[keys[-1]]
        except KeyError:
            return root_value

    async def set(
            self, 
            key: str, 
            value: Any, 
            
    ) -> None:
        """Set a value in the database using a hierarchical key.

        Parameters:
        key (str): The hierarchical key to insert or update, which may include nested levels separated by dots.
        value (Any): The value to be stored, which will be serialized to JSON.

        Returns:
        None

        Raises:
        asyncpg.PostgresError: If there is an error executing the query.
        """
        keys = key.split('.')

        root_key = keys[0]

        root_value = await self._get(root_key) or {}
        if not isinstance(root_value, dict):
            root_value = {}
        data = self._traverse_dict(root_value, keys[1:], create_missing=True)

        data[keys[-1]] = value

        await self._set(root_key, root_value)

    async def delete(
            self, 
            key: str, 
            
    ) -> bool:
        """Delete a value from the database using a hierarchical key.

        Parameters:
        key (str): The hierarchical key to delete, which may include nested levels separated by dots.

        Returns:
        bool: True if the key was deleted successfully, False otherwise.

        Raises:
        asyncpg.PostgresError: If there is an error executing the query.
        """
        keys = key.split('.')
        root_key = keys[0]
        root_value = await self._get(root_key)

        if root_value is None:
            return False
        

        data = self._traverse_dict(root_value, keys[1:])

        if keys[-1] in data:
            del data[keys[-1]]
            if data == {}:
                return await self._delete(key=root_key)
            
            await self._set(root_key, root_value)
            return True
        

        return await self._delete(
            key,
        )



    async def sum(
            self, 
            key: str, 
            value: float, 
            
    ) -> None:
        """Add a number to a stored value in the database.

        Parameters:
        key (str): The hierarchical key to update.
        value (float): The number to add.

        Returns:
        None

        Raises:
        ValueError: If the value or the stored value is not a number.
        asyncpg.PostgresError: If there is an error executing the query.
        """

        if not self._is_float(value):
            raise ValueError("The value should be an integer or float.")
        keys = key.split('.')
        root_key = keys[0]
        root_value = await self._get(root_key) or {}
        if not isinstance(root_value, dict):
            root_value = {}
        data = self._traverse_dict(root_value, keys[1:], create_missing=True)
        if not self._is_float(data.get(keys[-1], 0)):
            raise ValueError("The value at the key should be an integer or float.")
        
        data[keys[-1]] = data.get(keys[-1], 0) + value
        await self._set(root_key, root_value)

    async def sub(
            self, 
            key: str, 
            value: float, 
            
    ) -> None:
        """Subtract a number from a stored value in the database.

        Parameters:
        key (str): The hierarchical key to update.
        value (float): The number to subtract.

        Returns:
        None

        Raises:
        ValueError: If the value or the stored value is not a number.
        asyncpg.PostgresError: If there is an error executing the query.
        """
        if not self._is_float(value):
            raise ValueError("The value should be an integer or float.")


        keys = key.split('.')

        root_key = keys[0]
        root_value = await self._get(root_key) or {}
        if not isinstance(root_value, dict):
            root_value = {}
        data = self._traverse_dict(root_value, keys[1:], create_missing=True)
        if not self._is_float(data.get(keys[-1], 0)):
            raise ValueError("The value at the key should be an integer or float.")
        data[keys[-1]] = data.get(keys[-1], 0) - value
        await self._set(root_key, root_value)

    async def push(
        self, 
        key: str, 
        value: Any, 
        
    ) -> None:
        """Append a value to a list stored in the database.

        Parameters:
        key (str): The hierarchical key to append the value to.
        value (Any): The value to append.

        Returns:
        None

        Raises:
        ValueError: If the existing value at the key is not a list.
        asyncpg.PostgresError: If there is an error executing the query.
        """


        keys = key.split('.')

        root_key = keys[0]
        root_value = await self._get(root_key) or {}
        if not isinstance(root_value, dict):
            root_value = {}
        data = self._traverse_dict(root_value, keys[1:], create_missing=True)


        if not isinstance(data.get(keys[-1], []), Sequence):
            raise ValueError("The value at the key should be a list.")
        if data.get(keys[-1], []) == []:
            data[keys[-1]] = [value]
        else:

           data[keys[-1]].append(value)
        await self._set(root_key, root_value)
    
    async def pull(
        self, 
        key: str, 
        value: Any, 
        
    ) -> None:
        """Remove a value from a list stored in the database.

        Parameters:
        key (str): The hierarchical key to remove the value from.
        value (Any): The value to remove.

        Returns:
        None

        Raises:
        ValueError: If the existing value at the key is not a list.
        asyncpg.PostgresError: If there is an error executing the query.
        """


        keys = key.split('.')

        root_key = keys[0]
        root_value = await self._get(root_key) or {}
        if not isinstance(root_value, dict):
            root_value = {}
        data = self._traverse_dict(root_value, keys[1:], create_missing=True)



        if not isinstance(data.get(keys[-1], []), Sequence):
            raise ValueError("The value at the key should be a list.")
        if value in data.get(keys[-1], []):
           
           data[keys[-1]].remove(value)
        
        await self._set(root_key, root_value)


    async def _setup(
            self,

    ) -> None:
        """Set up the kv_table in the database.


        Returns:
        None

        Raises:
        asyncpg.PostgresError: If there is an error executing the query.
        """

        query = """
        CREATE TABLE IF NOT EXISTS kv_table (
            key TEXT UNIQUE,
            value JSONB
        );
        """

        await self._fetch(query)


            

    async def _get(
            self,
            key: str,

    ) -> Union[None, Any]:
        """Retrieve a value from the database based on the key.

        Parameters:
        key (str): The key to search for.

        Returns:
        Union[None, Any]: The value associated with the key, or None if the key does not exist.

        Raises:
        asyncpg.PostgresError: If there is an error executing the query.
        """

        query = """
        SELECT "value"
        FROM kv_table 
        WHERE "key" = $1;
        """


        result = await self._fetch(query, (key, ))
        
        if result:

            return json.loads(*result[0])

        return None
                


    async def _set(
            self,
            key: str,
            value: Any,
            

    ) -> None:
        """Set a value in the database for a specific key.

        Parameters:
        key (str): The key to insert or update.
        value (Any): The value to be stored, which will be serialized to JSON.

        Returns:
        None

        Raises:
        asyncpg.PostgresError: If there is an error executing the query.
        """

        value = json.dumps(value)


        query = """
        INSERT INTO kv_table ("key", "value")
        VALUES ($1, $2)
        ON CONFLICT ("key") DO UPDATE
        SET "value" = EXCLUDED."value";
        """

        await self._fetch(query, (key, value))

        
    
    async def _delete(
            self,
            key: str,
            

    ) -> bool:
        """Delete a key-value pair from the database.

        Parameters:
        key (str): The key to delete.

        Returns:
        bool: True if the key was deleted successfully, False otherwise.

        Raises:
        asyncpg.PostgresError: If there is an error executing the query.
        """


        old_value = await self._get(
            key,
        )


        query = """
        DELETE FROM kv_table
        WHERE "key" = CAST($1 AS TEXT);
        """

        await self._fetch(query, (key,))

        new_value = await self._get(
            key,
        )

        return old_value != new_value


    

    
    async def _sum(
            self,
            key: str,
            value: float,
            
            
    ) -> None:
        """Add a number to a stored value in the database.

        Parameters:
        key (str): The key to update.
        value (float): The number to add.

        Returns:
        None

        Raises:
        ValueError: If the value or the stored value is not a number.
        asyncpg.PostgresError: If there is an error executing the query.
        """

        old_value = await self._get(
            key,
        )

        if not self._is_float(value):
            raise ValueError("The value should be an integer or float")

        if old_value is not None:

            if not self._is_float(old_value):
                raise ValueError("The old value should be an integer or float")

            new_value = old_value + value
            return await self._set(
                key,
                new_value,
            )
        

        return await self._set(
            key,
            value,
        )
     
    async def _sub(
            self,
            key: str,
            value: float,
            
            
    ) -> None:
        """Subtract a number from a stored value in the database.

        Parameters:
        key (str): The key to update.
        value (float): The number to subtract.

        Returns:
        None

        Raises:
        ValueError: If the value or the stored value is not a number.
        asyncpg.PostgresError: If there is an error executing the query.
        """

        old_value = await self._get(
            key,
        )

        if not self._is_float(value):
            raise ValueError("The value should be an integer or float")

        if old_value is not None:

            if not self._is_float(old_value):
                raise ValueError("The old value should be an integer or float")

            new_value = old_value - value
            return await self._set(
                key,
                new_value,
            )
        

        return await self._set(
            key,
            value,
        )



    async def select_all(
            self,

    ) -> Sequence[Dict[str, Any]]:
        """Retrieve all key-value pairs from the kv_table.

        Returns:
        Sequence[Dict[str, Any]]: A list of dictionaries containing key-value pairs.


        Raises:
        asyncpg.PostgresError: If there is an error executing the query.
        """

        query = """
        SELECT * FROM kv_table;
        """

        rows = await self._fetch(query)
        
        values = [{row['key']: row['value']} for row in rows]
        
        return values


    async def __aenter__(
            self
    ) -> "KVDatabase":
        """Enter the runtime context related to this object.

        Returns:
        KVDatabase: The current instance of the class.
        """
        await self._setup()

        return self
    
    async def __aexit__(
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

        await self._connection.close()


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
    
    def _traverse_dict(
            self, 
            data: Dict, 
            keys: Sequence[str], 
            create_missing: bool = False
    ):
        """Traverse a dictionary to get or set a nested value based on keys.

        Parameters:
        data (Dict): The dictionary to traverse.
        keys (Sequence[str]): The sequence of keys to follow.
        create_missing (bool): Whether to create missing keys. Defaults to False.

        Returns:
        Union[Dict, Any]: The final dictionary or value at the end of the key sequence.
    
        """
        for key in keys[:-1]:
            if create_missing and key not in data:
                data[key] = {}
            data = data[key]
        return data

    def _load_query(
            self,
            name: str, 
            /
    ) -> str:
        """Load an SQL query from a file.

        Parameters:
        name (str): The name of the SQL file containing the query.

        Returns:
        str: The contents of the SQL file as a string.

        Raises:
        FileNotFoundError: If the file specified by `path` does not exist.
        IOError: If there is an error reading the file.
    
        """


        base_path = "./sql/keyvalue/"
        with open(base_path+name) as file:
            return file.read().strip()
        
    async def _fetch(
            self,
            query: str,
            values: Sequence[Any] = [],
            /
    ) -> list:
        """Execute a SQL query with the provided values and return the result.

        Parameters:
        query (str): The SQL query to execute.
        values (Sequence[Any]): The values to be used in the query (optional).

        Returns:
        Sequence[Dict[str, Any]]: The result of the query, where each row is represented as a dictionary.

        Raises:
        asyncpg.PostgresError: If there is an error executing the query.
        """


        return await self._connection.fetch(
            query,
            *values
        )
