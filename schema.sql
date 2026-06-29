-- ========================================================
-- DATABASE SCHEMA FOR TALENTREE AI PERSISTENCE & MEMORY
-- Run this script on your SQL Server (db39807) database.
-- ========================================================

-- 1. Create AiSessions Table (Tracks Chat Sessions per Business Profile)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AiSessions]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[AiSessions] (
        [Id] NVARCHAR(450) NOT NULL,
        [BusinessOwnerProfileId] INT NOT NULL,
        [Title] NVARCHAR(200) NOT NULL,
        [CreatedAt] DATETIME2 NOT NULL DEFAULT GETDATE(),
        [UpdatedAt] DATETIME2 NULL,
        CONSTRAINT [PK_AiSessions] PRIMARY KEY CLUSTERED ([Id] ASC),
        CONSTRAINT [FK_AiSessions_BusinessOwnerProfile] FOREIGN KEY ([BusinessOwnerProfileId]) 
            REFERENCES [dbo].[BusinessOwnerProfile] ([Id]) ON DELETE CASCADE
    );
    
    -- Optimize queries filtering sessions by profile
    CREATE NONCLUSTERED INDEX [IX_AiSessions_BusinessOwnerProfileId]
        ON [dbo].[AiSessions]([BusinessOwnerProfileId] ASC);
END
GO

-- 2. Create AiMessages Table (Tracks Full Conversation Message History)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AiMessages]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[AiMessages] (
        [Id] INT IDENTITY(1,1) NOT NULL,
        [SessionId] NVARCHAR(450) NOT NULL,
        [Role] NVARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
        [Content] NVARCHAR(MAX) NOT NULL,
        [CreatedAt] DATETIME2 NOT NULL DEFAULT GETDATE(),
        CONSTRAINT [PK_AiMessages] PRIMARY KEY CLUSTERED ([Id] ASC),
        CONSTRAINT [FK_AiMessages_AiSessions] FOREIGN KEY ([SessionId]) 
            REFERENCES [dbo].[AiSessions] ([Id]) ON DELETE CASCADE
    );

    -- Optimize queries pulling message history for active sessions
    CREATE NONCLUSTERED INDEX [IX_AiMessages_SessionId_CreatedAt]
        ON [dbo].[AiMessages]([SessionId] ASC, [CreatedAt] ASC);
END
GO

-- 3. Create AiAgentExecutions Table (Logs Sub-Agent Traces & Token Audits)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AiAgentExecutions]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[AiAgentExecutions] (
        [Id] INT IDENTITY(1,1) NOT NULL,
        [SessionId] NVARCHAR(450) NOT NULL,
        [AgentName] NVARCHAR(100) NOT NULL, -- e.g. 'MARKETING', 'PRICING', 'LOGO_GEN'
        [InputData] NVARCHAR(MAX) NULL,
        [OutputData] NVARCHAR(MAX) NULL,
        [ExecutionTimeMs] BIGINT NOT NULL,
        [CreatedAt] DATETIME2 NOT NULL DEFAULT GETDATE(),
        CONSTRAINT [PK_AiAgentExecutions] PRIMARY KEY CLUSTERED ([Id] ASC),
        CONSTRAINT [FK_AiAgentExecutions_AiSessions] FOREIGN KEY ([SessionId]) 
            REFERENCES [dbo].[AiSessions] ([Id]) ON DELETE CASCADE
    );

    -- Optimize performance reports and analytics audit queries
    CREATE NONCLUSTERED INDEX [IX_AiAgentExecutions_SessionId]
        ON [dbo].[AiAgentExecutions]([SessionId] ASC);
END
GO
