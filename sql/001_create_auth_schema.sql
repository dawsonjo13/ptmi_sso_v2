/*
Existing employee table is read-only and is not modified by this script.

Expected existing table:
employee(
    KPK varchar(6) primary key,
    name varchar(100),
    dob varchar(8),
    email varchar(255),
    supervisor varchar(6),
    join_date varchar(50)
)
*/

CREATE TABLE dbo.auth_user (
    id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    kpk varchar(6) NOT NULL UNIQUE,
    password_hash varchar(255) NOT NULL,
    is_active bit NOT NULL CONSTRAINT DF_auth_user_is_active DEFAULT 1,
    is_locked bit NOT NULL CONSTRAINT DF_auth_user_is_locked DEFAULT 0,
    failed_login_attempts int NOT NULL CONSTRAINT DF_auth_user_failed_login_attempts DEFAULT 0,
    last_login_at datetime2 NULL,
    password_changed_at datetime2 NULL,
    created_at datetime2 NOT NULL CONSTRAINT DF_auth_user_created_at DEFAULT SYSUTCDATETIME(),
    updated_at datetime2 NOT NULL CONSTRAINT DF_auth_user_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_auth_user_employee FOREIGN KEY (kpk) REFERENCES dbo.employee(KPK)
);
GO

CREATE INDEX IX_auth_user_kpk ON dbo.auth_user(kpk);
GO

CREATE TABLE dbo.auth_session (
    id uniqueidentifier NOT NULL CONSTRAINT DF_auth_session_id DEFAULT NEWID() PRIMARY KEY,
    auth_user_id bigint NOT NULL,
    refresh_token_hash varchar(255) NOT NULL,
    user_agent varchar(500) NULL,
    ip_address varchar(45) NULL,
    is_revoked bit NOT NULL CONSTRAINT DF_auth_session_is_revoked DEFAULT 0,
    revoked_at datetime2 NULL,
    expires_at datetime2 NOT NULL,
    created_at datetime2 NOT NULL CONSTRAINT DF_auth_session_created_at DEFAULT SYSUTCDATETIME(),
    last_used_at datetime2 NULL,
    CONSTRAINT FK_auth_session_auth_user FOREIGN KEY (auth_user_id) REFERENCES dbo.auth_user(id)
);
GO

CREATE INDEX IX_auth_session_auth_user_id ON dbo.auth_session(auth_user_id);
CREATE INDEX IX_auth_session_refresh_token_hash ON dbo.auth_session(refresh_token_hash);
CREATE INDEX IX_auth_session_expires_at ON dbo.auth_session(expires_at);
GO

CREATE TABLE dbo.password_reset_token (
    id uniqueidentifier NOT NULL CONSTRAINT DF_password_reset_token_id DEFAULT NEWID() PRIMARY KEY,
    auth_user_id bigint NOT NULL,
    token_hash varchar(255) NOT NULL,
    is_used bit NOT NULL CONSTRAINT DF_password_reset_token_is_used DEFAULT 0,
    used_at datetime2 NULL,
    expires_at datetime2 NOT NULL,
    created_at datetime2 NOT NULL CONSTRAINT DF_password_reset_token_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_password_reset_token_auth_user FOREIGN KEY (auth_user_id) REFERENCES dbo.auth_user(id)
);
GO

CREATE INDEX IX_password_reset_token_auth_user_id ON dbo.password_reset_token(auth_user_id);
CREATE INDEX IX_password_reset_token_token_hash ON dbo.password_reset_token(token_hash);
CREATE INDEX IX_password_reset_token_expires_at ON dbo.password_reset_token(expires_at);
GO
