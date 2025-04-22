-- =======================================================================
--  Setup script for database "fisina"
--  Cleaned & deduplicated on 2025-04-22
-- =======================================================================

-------------------------------------------------------------------------
-- 0.  (Optional) create the role beforehand if it doesn’t exist
--     CREATE ROLE jorgeavlobo LOGIN PASSWORD '******';
-------------------------------------------------------------------------

-------------------------------------------------------------------------
-- 1.  Create the database  (run once as super‑user)
-------------------------------------------------------------------------
CREATE DATABASE fisina
    OWNER      = jorgeavlobo
    ENCODING   = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE   = 'en_US.UTF-8'
    TEMPLATE   = template0;

\connect fisina

-------------------------------------------------------------------------
-- 2.  Global settings
-------------------------------------------------------------------------
ALTER DATABASE fisina SET timezone TO 'UTC';
ALTER ROLE     jorgeavlobo SET timezone TO 'UTC';

-- Work in the public schema by default
SET search_path = public;

-------------------------------------------------------------------------
-- 3.  Extensions  (run once per database)
-------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID v1/v4 generator
CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;        -- case‑insensitive text

-------------------------------------------------------------------------
-- 4.  Privileges & defaults
-------------------------------------------------------------------------
GRANT ALL ON SCHEMA public TO jorgeavlobo;

ALTER DEFAULT PRIVILEGES
    GRANT ALL ON TABLES    TO jorgeavlobo;
ALTER DEFAULT PRIVILEGES
    GRANT ALL ON SEQUENCES TO jorgeavlobo;
ALTER DEFAULT PRIVILEGES
    GRANT ALL ON FUNCTIONS TO jorgeavlobo;
ALTER DEFAULT PRIVILEGES
    GRANT ALL ON TYPES     TO jorgeavlobo;

-------------------------------------------------------------------------
-- 5.  Tables & business logic
-------------------------------------------------------------------------

/* 5.1  USERS ---------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS public.users (
    user_id             UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name          VARCHAR(100)   NOT NULL,
    last_name           VARCHAR(100)   NOT NULL,

    telegram_user_id    BIGINT,
    tax_id_number       VARCHAR(30)    UNIQUE,
    moloni_customer_id  INTEGER        UNIQUE,

    created_at          TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- telegram_user_id is only unique when present
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_telegram_id
    ON public.users (telegram_user_id)
    WHERE telegram_user_id IS NOT NULL;

/* 5.2  ROLES ---------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS roles (
    role_id   SERIAL        PRIMARY KEY,
    role_name VARCHAR(50)   NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID    NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL
        REFERENCES roles(role_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

/* 5.3  EMAILS --------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS user_emails (
    email_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID  NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    email      CITEXT NOT NULL UNIQUE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE
);

-- only one primary email per user
CREATE UNIQUE INDEX IF NOT EXISTS ux_user_emails_primary
    ON user_emails (user_id)
    WHERE is_primary;

/* 5.4  PHONES --------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS user_phones (
    phone_id     SERIAL PRIMARY KEY,
    user_id      UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    phone_number VARCHAR(50) NOT NULL UNIQUE,
    is_primary   BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_user_phones_primary
    ON user_phones (user_id)
    WHERE is_primary;

/* 5.5  ADDRESSES ------------------------------------------------------ */
CREATE TABLE IF NOT EXISTS addresses (
    address_id    SERIAL PRIMARY KEY,
    user_id       UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    country       VARCHAR(100),
    city          VARCHAR(100),
    postal_code   VARCHAR(20),
    street        VARCHAR(100),
    street_number VARCHAR(50),
    lat           NUMERIC(9,6),
    lon           NUMERIC(9,6),
    is_primary    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_addresses_primary
    ON addresses (user_id)
    WHERE is_primary;

/* 5.6  CAREGIVER ↔ PATIENT ------------------------------------------- */
CREATE TABLE IF NOT EXISTS caregiver_patients (
    caregiver_id UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    patient_id   UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    PRIMARY KEY (caregiver_id, patient_id)
);

-- trigger to enforce caregiver & patient roles
CREATE OR REPLACE FUNCTION trg_check_caregiver_roles() RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM user_roles ur
        JOIN roles r ON r.role_id = ur.role_id
        WHERE ur.user_id = NEW.caregiver_id
          AND r.role_name = 'caregiver'
    ) THEN
        RAISE EXCEPTION 'User % is not a caregiver', NEW.caregiver_id;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM user_roles ur
        JOIN roles r ON r.role_id = ur.role_id
        WHERE ur.user_id = NEW.patient_id
          AND r.role_name = 'patient'
    ) THEN
        RAISE EXCEPTION 'User % is not a patient', NEW.patient_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER check_caregiver_patient_roles
AFTER INSERT OR UPDATE ON caregiver_patients
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION trg_check_caregiver_roles();

/* 5.7  THERAPIST ↔ PATIENT ------------------------------------------- */
CREATE TABLE IF NOT EXISTS therapist_patients (
    physiotherapist_id UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    patient_id         UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    PRIMARY KEY (physiotherapist_id, patient_id)
);

CREATE OR REPLACE FUNCTION trg_check_therapist_role() RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM user_roles ur
        JOIN roles r ON r.role_id = ur.role_id
        WHERE ur.user_id = NEW.physiotherapist_id
          AND r.role_name = 'physiotherapist'
    ) THEN
        RAISE EXCEPTION 'User % is not a physiotherapist', NEW.physiotherapist_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER check_therapist_role
AFTER INSERT OR UPDATE ON therapist_patients
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION trg_check_therapist_role();

-------------------------------------------------------------------------
-- Done!
-------------------------------------------------------------------------
