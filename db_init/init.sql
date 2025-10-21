-- db_init/init.sql

-- Create DB (optional if not using POSTGRES_DB)
CREATE DATABASE fraudshield_db;

-- Create user
CREATE USER fraud_user WITH PASSWORD 'fraudpass';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE fraudshield_db TO fraud_user;
