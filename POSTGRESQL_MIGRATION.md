# PostgreSQL Migration Guide

This guide will help you migrate your attendance system from SQLite to PostgreSQL.

## Prerequisites

1. **Install PostgreSQL** on your system:
   - **Windows**: Download from https://www.postgresql.org/download/windows/
   - **macOS**: `brew install postgresql`
   - **Linux**: `sudo apt-get install postgresql postgresql-contrib`

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Step 1: Create PostgreSQL Database

1. **Start PostgreSQL service**
2. **Create a new database**:
   ```sql
   CREATE DATABASE attendance_db;
   CREATE USER attendance_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE attendance_db TO attendance_user;
   ```

## Step 2: Configure Environment Variables

1. **Create a `.env` file** in your project root (copy from `env_template.txt`):
   ```env
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=postgresql://attendance_user:your_password@localhost:5432/attendance_db
   ```

2. **Update the values** with your actual PostgreSQL credentials.

## Step 3: Run the Setup Script

```bash
python setup_postgresql.py
```

This script will:
- Check your PostgreSQL connection
- Create database tables
- Run migrations

## Step 4: Migrate Existing Data (Optional)

If you have existing data in SQLite that you want to migrate:

1. **Export SQLite data**:
   ```bash
   sqlite3 instance/attendance.db ".dump" > sqlite_backup.sql
   ```

2. **Convert and import to PostgreSQL** (manual process):
   - Convert SQLite syntax to PostgreSQL syntax
   - Import the converted SQL file

## Step 5: Test the Application

```bash
python run.py
```

## Troubleshooting

### Common Issues:

1. **Connection Error**: Make sure PostgreSQL is running and credentials are correct
2. **Permission Error**: Ensure the database user has proper privileges
3. **Port Issues**: Default PostgreSQL port is 5432, make sure it's not blocked

### Fallback to SQLite:

If you need to temporarily use SQLite again, update your `.env` file:
```env
DATABASE_URL=sqlite:///attendance.db
```

## Production Deployment

For production deployment:

1. **Use environment variables** for database credentials
2. **Set up proper PostgreSQL security** (firewall, SSL, etc.)
3. **Configure connection pooling** if needed
4. **Set up regular backups**

## Database URL Formats

- **Local PostgreSQL**: `postgresql://username:password@localhost:5432/database_name`
- **Remote PostgreSQL**: `postgresql://username:password@host:port/database_name`
- **Heroku**: `postgresql://username:password@host:port/database_name`

## Migration Commands

```bash
# Initialize migrations (if not already done)
flask db init

# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```
