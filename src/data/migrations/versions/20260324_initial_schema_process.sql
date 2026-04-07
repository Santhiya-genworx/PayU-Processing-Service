DO $$ BEGIN CREATE TYPE po_status_enum AS ENUM ('pending', 'completed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN CREATE TYPE matching_status_enum AS ENUM ('pending', 'approved', 'rejected', 'reviewed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN CREATE TYPE decision_status_enum AS ENUM ('approve', 'reject', 'review');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255)    NOT NULL,
    email       VARCHAR(255)    NOT NULL UNIQUE,
    password    VARCHAR(255)    NOT NULL,
    role        VARCHAR(50)       NOT NULL,
    is_active   BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vendors (
    id                   SERIAL PRIMARY KEY,
    name                 VARCHAR(255)    NOT NULL,
    email                VARCHAR(255)    NOT NULL UNIQUE,
    address              VARCHAR(255)    NOT NULL,
    country_code         VARCHAR(3)      NOT NULL,
    mobile_number        VARCHAR(20)     NOT NULL,
    gst_number           VARCHAR(15)     NOT NULL UNIQUE,
    bank_name            VARCHAR(255)    NOT NULL,
    account_holder_name  VARCHAR(255)    NOT NULL,
    account_number       VARCHAR(50)     NOT NULL,
    ifsc_code            VARCHAR(20)     NOT NULL,
    created_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id       VARCHAR(255)    PRIMARY KEY,
    vendor_id        INTEGER         NOT NULL REFERENCES vendors(id),
    invoice_date     DATE            NOT NULL,
    due_date         DATE            NOT NULL,
    currency_code    VARCHAR(3)      NOT NULL,
    subtotal         NUMERIC(15, 2)  NOT NULL,
    tax_amount       NUMERIC(15, 2)  NOT NULL,
    discount_amount  NUMERIC(15, 2),
    total_amount     NUMERIC(15, 2)  NOT NULL,
    file_url         VARCHAR(255)    NOT NULL,
    created_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoices_vendor_id ON invoices (vendor_id);

CREATE TABLE IF NOT EXISTS invoice_items (
    item_id           SERIAL PRIMARY KEY,
    invoice_id        VARCHAR(255)    NOT NULL REFERENCES invoices(invoice_id),
    item_description  VARCHAR(255)    NOT NULL,
    quantity          INTEGER,
    unit_price        NUMERIC(15, 2),
    total_price       NUMERIC(15, 2)  NOT NULL,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id ON invoice_items (invoice_id);

CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id          VARCHAR(255)    PRIMARY KEY,
    vendor_id      INTEGER         NOT NULL REFERENCES vendors(id),
    gl_code        VARCHAR(255)    NOT NULL,
    total_amount   NUMERIC(15, 2)  NOT NULL,
    currency_code  VARCHAR(3)      NOT NULL,
    ordered_date   DATE            NOT NULL,
    file_url       VARCHAR(255)    NOT NULL,
    status         po_status_enum  NOT NULL,
    created_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_purchase_orders_vendor_id ON purchase_orders (vendor_id);

CREATE TABLE IF NOT EXISTS ordered_items (
    item_id           SERIAL PRIMARY KEY,
    po_id             VARCHAR(255)    NOT NULL REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
    item_description  VARCHAR(255)    NOT NULL,
    quantity          INTEGER         NOT NULL,
    unit_price        NUMERIC(15, 2)  NOT NULL,
    total_price       NUMERIC(15, 2)  NOT NULL,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ordered_items_po_id ON ordered_items (po_id);

CREATE TABLE IF NOT EXISTS invoice_upload_history (
    id           SERIAL PRIMARY KEY,
    invoice_id   VARCHAR(255)    NOT NULL REFERENCES invoices(invoice_id),
    old_file_url VARCHAR(255)    NOT NULL,
    new_file_url VARCHAR(255)    NOT NULL,
    action_date  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoice_upload_history_invoice_id ON invoice_upload_history (invoice_id);

CREATE TABLE IF NOT EXISTS purchase_order_upload_history (
    id           SERIAL PRIMARY KEY,
    po_id        VARCHAR(255)    NOT NULL REFERENCES purchase_orders(po_id),
    old_file_url VARCHAR(255)    NOT NULL,
    new_file_url VARCHAR(255)    NOT NULL,
    action_date  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_po_upload_history_po_id ON purchase_order_upload_history (po_id);

CREATE TABLE IF NOT EXISTS invoice_matching (
    id                SERIAL PRIMARY KEY,
    invoices          TEXT[]                  NOT NULL DEFAULT '{}',
    pos               TEXT[]                  NOT NULL DEFAULT '{}',
    is_po_matched     BOOLEAN                 NULL,          -- NULL = waiting, TRUE = ready
    status            matching_status_enum    NOT NULL DEFAULT 'pending',
    decision          decision_status_enum,
    command           VARCHAR(255),
    confidence_score  NUMERIC(10, 2),
    mail_to           VARCHAR(255),
    mail_subject      VARCHAR(255),
    mail_body         TEXT,
    matched_at        TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ             NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoice_matching_invoices ON invoice_matching USING GIN (invoices);
CREATE INDEX IF NOT EXISTS idx_invoice_matching_pos     ON invoice_matching USING GIN (pos);
CREATE INDEX IF NOT EXISTS idx_invoice_matching_status  ON invoice_matching (status);
