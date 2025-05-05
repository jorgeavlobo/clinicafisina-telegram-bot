-- ======================================================================
--  Setup script for database  F I S I N A           (v2 – 2025-04-23)
--  Includes all refinements: UTC, UUID PKs, updated_at, constraints …
-- ======================================================================

------------------------------------------------------------------
-- 0. (Opcional) criar a role do proprietário se ainda não existir
--    CREATE ROLE jorgeavlobo LOGIN PASSWORD '•••••';
------------------------------------------------------------------

------------------------------------------------------------------
-- 1. Criar a base de dados  (executa apenas uma vez, como super-user)
------------------------------------------------------------------
CREATE DATABASE fisina
    OWNER      = jorgeavlobo
    ENCODING   = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE   = 'en_US.UTF-8'
    TEMPLATE   = template0;

\connect fisina

------------------------------------------------------------------
-- 2. Definições globais
------------------------------------------------------------------
ALTER DATABASE fisina    SET timezone TO 'UTC';
ALTER ROLE     jorgeavlobo SET timezone TO 'UTC';
SET search_path = public;

------------------------------------------------------------------
-- 3. Extensões (uma vez por BD)
------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

------------------------------------------------------------------
-- 4. Privilegios & defaults
------------------------------------------------------------------
GRANT ALL ON SCHEMA public TO jorgeavlobo;

ALTER DEFAULT PRIVILEGES GRANT ALL ON TABLES    TO jorgeavlobo;
ALTER DEFAULT PRIVILEGES GRANT ALL ON SEQUENCES TO jorgeavlobo;
ALTER DEFAULT PRIVILEGES GRANT ALL ON FUNCTIONS TO jorgeavlobo;
ALTER DEFAULT PRIVILEGES GRANT ALL ON TYPES     TO jorgeavlobo;

------------------------------------------------------------------
-- 5. Utilitários genéricos
------------------------------------------------------------------
/* 5.1 updated_at trigger ---------------------------------------- */
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

/* 5.2 helper para ligar telegram_user_id ao número de telefone --- */
CREATE OR REPLACE FUNCTION link_telegram(
        p_user UUID,
        p_phone VARCHAR,
        p_tgid BIGINT
) RETURNS VOID AS $$
INSERT INTO user_phones (user_id, phone_number, telegram_user_id)
VALUES (p_user, p_phone, p_tgid)
ON CONFLICT (phone_number)
    DO UPDATE SET telegram_user_id = EXCLUDED.telegram_user_id,
                  updated_at       = now();
$$ LANGUAGE sql;

------------------------------------------------------------------
-- 6. Tabelas de domínio
------------------------------------------------------------------

/* 6.1 USERS ------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS users (
    user_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    date_of_birth       DATE,

    tax_id_number       VARCHAR(30) UNIQUE,
    moloni_customer_id  INTEGER UNIQUE,

    created_by          UUID REFERENCES users(user_id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_users_updated
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

/* 6.2 ROLES ------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS roles (
    role_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL UNIQUE           -- 'patient', …
);

/* 6.3 USER_ROLES  (M:N) ------------------------------------------ */
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    role_id UUID NOT NULL
        REFERENCES roles(role_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER trg_user_roles_updated
BEFORE UPDATE ON user_roles
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

/* 6.4 E-MAILS ----------------------------------------------------- */
CREATE TABLE IF NOT EXISTS user_emails (
    email_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    email       CITEXT NOT NULL,
    is_primary  BOOLEAN NOT NULL DEFAULT FALSE,

    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_user_emails_format
        CHECK (email ~* '^[^@]+@[^@]+\.[a-z0-9]{2,}$')
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_user_emails_per_user
    ON user_emails(user_id, email);

CREATE UNIQUE INDEX IF NOT EXISTS ux_user_emails_primary
    ON user_emails(user_id)
    WHERE is_primary;

CREATE TRIGGER trg_user_emails_updated
BEFORE UPDATE ON user_emails
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

/* 6.5 PHONES ------------------------------------------------------ */
CREATE TABLE IF NOT EXISTS user_phones (
    phone_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    phone_number      VARCHAR(20) NOT NULL,
    telegram_user_id  BIGINT UNIQUE,
    is_primary        BOOLEAN NOT NULL DEFAULT FALSE,

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_user_phones_format
        CHECK (phone_number ~ '^[1-9][0-9]{6,14}$')
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_user_phones_per_user
    ON user_phones(user_id, phone_number);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_phones_telegram_uid
    ON user_phones(telegram_user_id);

CREATE UNIQUE INDEX IF NOT EXISTS ux_user_phones_primary
    ON user_phones(user_id)
    WHERE is_primary;

CREATE TRIGGER trg_user_phones_updated
BEFORE UPDATE ON user_phones
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

/* 6.6 ADDRESSES --------------------------------------------------- */
CREATE TABLE IF NOT EXISTS addresses (
    address_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,

    label          TEXT,                          -- 'home', 'work', …
    country        VARCHAR(100),
    city           VARCHAR(100),
    postal_code    VARCHAR(20),
    street         VARCHAR(100),
    street_number  VARCHAR(50),
    latitude       NUMERIC(9,6),
    longitude      NUMERIC(9,6),
    is_primary     BOOLEAN NOT NULL DEFAULT FALSE,

    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_addresses_primary
    ON addresses(user_id)
    WHERE is_primary;

CREATE TRIGGER trg_addresses_updated
BEFORE UPDATE ON addresses
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

/* 6.7 CAREGIVER ⟷ PATIENT  (M:N) -------------------------------- */
CREATE TABLE IF NOT EXISTS caregiver_patients (
    caregiver_id UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    patient_id   UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    PRIMARY KEY (caregiver_id, patient_id),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER trg_caregiver_patients_updated
BEFORE UPDATE ON caregiver_patients
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

/*  trigger para garantir papéis correctos */
CREATE OR REPLACE FUNCTION trg_check_caregiver_roles() RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM user_roles ur
        JOIN roles r USING(role_id)
        WHERE ur.user_id = NEW.caregiver_id
          AND r.role_name = 'caregiver'
    ) THEN
        RAISE EXCEPTION 'User % is not a caregiver', NEW.caregiver_id;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM user_roles ur
        JOIN roles r USING(role_id)
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
FOR EACH ROW EXECUTE FUNCTION trg_check_caregiver_roles();

/* 6.8 THERAPIST ⟷ PATIENT  (M:N) -------------------------------- */
CREATE TABLE IF NOT EXISTS therapist_patients (
    physiotherapist_id UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    patient_id         UUID NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    PRIMARY KEY (physiotherapist_id, patient_id),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER trg_therapist_patients_updated
BEFORE UPDATE ON therapist_patients
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

/*  trigger para garantir papel de fisioterapeuta */
CREATE OR REPLACE FUNCTION trg_check_therapist_role() RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM user_roles ur
        JOIN roles r USING(role_id)
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
FOR EACH ROW EXECUTE FUNCTION trg_check_therapist_role();

------------------------------------------------------------------
-- 7. Dados de arranque
------------------------------------------------------------------
INSERT INTO roles(role_name) VALUES
  ('patient'),
  ('caregiver'),
  ('physiotherapist'),
  ('accountant'),
  ('administrator')
ON CONFLICT DO NOTHING;

------------------------------------------------------------------
-- 8. Vistas auxiliares (faculta-tivo)
------------------------------------------------------------------
CREATE OR REPLACE VIEW v_user_roles AS
SELECT u.user_id,
       json_agg(r.role_name ORDER BY r.role_name) AS roles
FROM   users u
JOIN   user_roles ur USING(user_id)
JOIN   roles r USING(role_id)
GROUP  BY u.user_id;

------------------------------------------------------------------
-- Feito!            psql  -d fisina  -f 001_fisina_setup.sql
------------------------------------------------------------------
