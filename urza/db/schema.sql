-- /urza/db/schema.sql

-- User Roles Table
CREATE TABLE IF NOT EXISTS user_roles (
    name VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL,
    admin BOOLEAN DEFAULT FALSE,
    can_create_hidden BOOLEAN DEFAULT FALSE,
    can_see_hidden BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    role_name VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_id VARCHAR(36) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_hidden BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (role_name) REFERENCES user_roles(name),
    FOREIGN KEY (created_by_id) REFERENCES users(user_id)
);

-- API Keys Table
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    hashed_key VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_id VARCHAR(36) NOT NULL,
    last_used TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_hidden BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (created_by_id) REFERENCES users(user_id)
);

-- Platforms Table
CREATE TABLE IF NOT EXISTS platforms (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    os_major_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Capabilities Table
CREATE TABLE IF NOT EXISTS capabilities (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bots Table
CREATE TABLE IF NOT EXISTS bots (
    bot_id VARCHAR(36) PRIMARY KEY,
    created_by_id VARCHAR(36) NOT NULL,
    platform_id VARCHAR(36) NOT NULL,
    tg_bot_username VARCHAR(100) UNIQUE NOT NULL,
    tg_bot_token VARCHAR(255) NOT NULL,
    capabilities JSON NOT NULL,
    last_checkin TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_hidden BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (created_by_id) REFERENCES users(user_id),
    FOREIGN KEY (platform_id) REFERENCES platforms(id)
);

-- Notification Configs Table
CREATE TABLE IF NOT EXISTS notification_configs (
    id VARCHAR(36) PRIMARY KEY,
    profile_name VARCHAR(100) NOT NULL,
    profile_description TEXT,
    created_by_id VARCHAR(36) NOT NULL,
    webhook_url VARCHAR(500),
    telegram_chat_id VARCHAR(100),
    slack_webhook_url VARCHAR(500),
    slack_channel VARCHAR(100),
    notify_on_task_completed BOOLEAN DEFAULT TRUE,
    notify_on_task_error BOOLEAN DEFAULT TRUE,
    notify_on_task_timeout BOOLEAN DEFAULT TRUE,
    notify_on_bot_offline BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by_id) REFERENCES users(user_id)
);

-- Tasks Table
CREATE TABLE IF NOT EXISTS tasks (
    task_id VARCHAR(36) PRIMARY KEY,
    config JSON NOT NULL,
    capability_id VARCHAR(36) NOT NULL,
    platform_id VARCHAR(36) NOT NULL,
    created_by_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notification_config_id VARCHAR(36),
    next_run TIMESTAMP NULL,
    last_run TIMESTAMP NULL,
    timeout_seconds INT DEFAULT 3600,
    cron_schedule VARCHAR(100),
    proof_of_work_required BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_hidden BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (capability_id) REFERENCES capabilities(id),
    FOREIGN KEY (platform_id) REFERENCES platforms(id),
    FOREIGN KEY (created_by_id) REFERENCES users(user_id),
    FOREIGN KEY (notification_config_id) REFERENCES notification_configs(id)
);

-- Proof of Work Table
CREATE TABLE IF NOT EXISTS proof_of_work (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    link VARCHAR(500) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Task Executions Table
CREATE TABLE IF NOT EXISTS task_executions (
    execution_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    created_by_id VARCHAR(36) NOT NULL,
    assigned_to VARCHAR(100),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    status ENUM('broadcasted', 'claimed', 'in_progress', 'completed', 'failed', 'timedout') DEFAULT 'broadcasted',
    proof_of_work_id VARCHAR(36),
    error_message TEXT,
    results JSON,
    retry_count INT DEFAULT 0,
    is_hidden BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (created_by_id) REFERENCES users(user_id),
    FOREIGN KEY (proof_of_work_id) REFERENCES proof_of_work(id)
);

-- Indexes for performance
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_hashed ON api_keys(hashed_key);
CREATE INDEX idx_bots_created_by ON bots(created_by_id);
CREATE INDEX idx_bots_platform ON bots(platform_id);
CREATE INDEX idx_tasks_created_by ON tasks(created_by_id);
CREATE INDEX idx_task_executions_task ON task_executions(task_id);
CREATE INDEX idx_task_executions_status ON task_executions(status);