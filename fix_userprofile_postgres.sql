-- Fix UserProfile primary key issue in PostgreSQL
-- This script fixes the phone field primary key constraint

-- Step 1: Check current constraints
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'accounts_app_userprofile';

-- Step 2: Add id column as primary key
ALTER TABLE accounts_app_userprofile ADD COLUMN id BIGSERIAL PRIMARY KEY;

-- Step 3: Drop the existing primary key constraint on phone
ALTER TABLE accounts_app_userprofile DROP CONSTRAINT accounts_app_userprofile_pkey;

-- Step 4: Make phone column nullable
ALTER TABLE accounts_app_userprofile ALTER COLUMN phone DROP NOT NULL;

-- Step 5: Update empty phone values to NULL
UPDATE accounts_app_userprofile SET phone = NULL WHERE phone = '';

-- Step 6: Verify the changes
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'accounts_app_userprofile'
ORDER BY ordinal_position;
