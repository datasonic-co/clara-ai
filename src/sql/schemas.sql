CREATE TABLE `assistant-db`.users (
    `id` CHAR(36) PRIMARY KEY,
    `identifier` TEXT NOT NULL UNIQUE,
    `metadata` JSON NOT NULL,
    `createdAt` TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `assistant-db`.threads (
    `id` CHAR(36) PRIMARY KEY,
    `createdAt` TEXT,
    `name` TEXT,
    `userId` CHAR(36),
    `userIdentifier` TEXT,
    `tags` TEXT,
    `metadata` JSON,
    FOREIGN KEY (`userId`) REFERENCES `assistant-db`.users(`id`) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS `assistant-db`.steps (
    `id` CHAR(36) PRIMARY KEY,
    `name` TEXT NOT NULL,
    `type` TEXT NOT NULL,
    `threadId` CHAR(36) NOT NULL,
    `parentId` CHAR(36),
    `disableFeedback` BOOLEAN NOT NULL,
    `streaming` BOOLEAN NOT NULL,
    `waitForAnswer` BOOLEAN,
    `isError` BOOLEAN,
    `metadata` JSON,
    `tags` TEXT,
    `input` TEXT,
    `output` TEXT,
    `createdAt` TEXT,
    `start` TEXT,
    `end` TEXT,
    `generation` JSON,
    `showInput` TEXT,
    `language` TEXT,
    `indent` INT
);

CREATE TABLE IF NOT EXISTS `assistant-db`.elements (
    `id` CHAR(36) PRIMARY KEY,
    `threadId` CHAR(36),
    `type` TEXT,
    `url` TEXT,
    `chainlitKey` TEXT,
    `name` TEXT NOT NULL,
    `display` TEXT,
    `objectKey` TEXT,
    `size` TEXT,
    `page` INT,
    `language` TEXT,
    `forId` CHAR(36),
    `mime` TEXT
);

CREATE TABLE IF NOT EXISTS `assistant-db`.feedbacks (
    `id` CHAR(36) PRIMARY KEY,
    `forId` CHAR(36) NOT NULL,
    `threadId` CHAR(36) NOT NULL,
    `value` INT NOT NULL,
    `comment` TEXT
);
