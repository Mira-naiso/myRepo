ALTER TABLE braintree_transaction ADD COLUMN income_tx_uuid binary(16) NULL COMMENT 'uuid', ALGORITHM=INSTANT;
ALTER TABLE customers DROP COLUMN middle_name;