import os
from flask_script import Manager, Server
from flask_migrate import MigrateCommand, Migrate
from app import app, db

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    print("Manager")
    manager.run()