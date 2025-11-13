-- Añadir campos page_id e instagram_account_id a social_tokens
ALTER TABLE social_tokens 
ADD COLUMN page_id VARCHAR(100) AFTER username,
ADD COLUMN instagram_account_id VARCHAR(100) AFTER page_id;
