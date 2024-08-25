"""
Xynus: A Comprehensive Discord Bot

This project is a Discord bot designed to handle a variety of tasks, ranging from message moderation to music playback. 
The bot is organized into multiple modules and submodules to ensure clean and maintainable code.

Modules:
---------
- archive:
    Contains scripts for archiving data, including database interactions.

- bot:
    Core functionality of the bot is defined here, including:
    - core: Handles the main client setup, logging, and bot settings.
    - handlers: Manages error handling and other event-based responses.
    - templates: Provides templates for common Discord interactions like buttons, embeds, modals, and views.
    - utils: Utility functions and configuration management.

- data:
    Contains static data used by the bot, such as emoji mappings in YAML format.

- extensions:
    Houses additional bot features organized into different extensions, such as:
    - messages: Commands and handlers related to messaging, moderation, and music.
    - private: Private or restricted commands and features.

- sql:
    SQL scripts used for database setup and maintenance, including ticketing system setup.

Other Files:
------------
- Dockerfile: Docker configuration for containerizing the bot.
- docker-compose.yml: Docker Compose configuration for managing multi-container Docker applications.
- main.py: The main entry point for starting the bot.
- requirements.txt: List of Python dependencies required for the project.
- test.py: Contains tests to ensure the bot’s functionality.
"""


__name__ = "bot"
__version__ = "1.5.4" 
