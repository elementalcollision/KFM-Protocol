-- KFM-AE Initial Schema - Version 1

-- Create ENUM type for lifecycle states (from subtask 1.1)
CREATE TYPE lifecycle_state_enum AS ENUM (
    'NEW',
    'EXPERIMENTAL',
    'CANDIDATE',
    'STABLE',
    'DEPRECATED',
    'ARCHIVED',
    'KILLED'
);

-- Create Agents table (from subtask 1.1)
CREATE TABLE Agents (
    unique_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(255) NOT NULL,
    version VARCHAR(255) NOT NULL,
    owner VARCHAR(255), -- Nullable
    maintainer VARCHAR(255), -- Nullable
    lifecycle_state lifecycle_state_enum NOT NULL DEFAULT 'NEW',
    creation_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_version_not_empty CHECK (version <> ''),
    CONSTRAINT chk_type_not_empty CHECK (type <> '')
);

COMMENT ON COLUMN Agents.unique_id IS 'Unique identifier for the agent (Primary Key)';
COMMENT ON COLUMN Agents.type IS 'Type of the agent (e.g., Software Artifact, AI Model). Refers to PRD section 3.1.';
COMMENT ON COLUMN Agents.version IS 'Version identifier for the agent (e.g., semantic version, git hash).';
COMMENT ON COLUMN Agents.owner IS 'Identifier for the owner/team responsible for the agent.';
COMMENT ON COLUMN Agents.maintainer IS 'Identifier for the specific maintainer/contact person.';
COMMENT ON COLUMN Agents.lifecycle_state IS 'Current KFM lifecycle state of the agent. Refers to PRD section 3.3.';
COMMENT ON COLUMN Agents.creation_timestamp IS 'Timestamp when the agent record was first created in the registry.';


-- Create AgentMetadata table (from subtask 1.2)
CREATE TABLE AgentMetadata (
    id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB,
    value_type VARCHAR(50), -- Nullable

    CONSTRAINT fk_agent
        FOREIGN KEY(agent_id)
        REFERENCES Agents(unique_id)
        ON DELETE CASCADE,

    CONSTRAINT unique_agent_key UNIQUE (agent_id, key)
);

COMMENT ON COLUMN AgentMetadata.id IS 'Surrogate primary key for the metadata entry';
COMMENT ON COLUMN AgentMetadata.agent_id IS 'Foreign key referencing the unique_id of the agent in the Agents table';
COMMENT ON COLUMN AgentMetadata.key IS 'The name (key) of the metadata attribute';
COMMENT ON COLUMN AgentMetadata.value IS 'The value of the metadata attribute, stored as JSONB for flexibility';
COMMENT ON COLUMN AgentMetadata.value_type IS 'Optional type hint for the value (e.g., string, number, boolean, json)';
COMMENT ON CONSTRAINT fk_agent ON AgentMetadata IS 'Ensures referential integrity with the Agents table. Metadata is deleted if the parent agent is deleted.';
COMMENT ON CONSTRAINT unique_agent_key ON AgentMetadata IS 'Ensures that each metadata key is unique per agent.';


-- Create StateTransitionLog table (from subtask 1.4)
CREATE TABLE StateTransitionLog (
    id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL,
    previous_state lifecycle_state_enum, -- Nullable for initial creation
    new_state lifecycle_state_enum NOT NULL,
    transition_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    triggering_agent_id UUID, -- Optional: Agent triggering change
    triggering_user_id VARCHAR(255), -- Optional: User triggering change
    justification TEXT,

    CONSTRAINT fk_log_agent
        FOREIGN KEY(agent_id)
        REFERENCES Agents(unique_id)
        ON DELETE CASCADE
);

COMMENT ON COLUMN StateTransitionLog.id IS 'Surrogate primary key for the state transition log entry';
COMMENT ON COLUMN StateTransitionLog.agent_id IS 'FK referencing the agent whose state transitioned';
COMMENT ON COLUMN StateTransitionLog.previous_state IS 'State before transition (NULL for initial)';
COMMENT ON COLUMN StateTransitionLog.new_state IS 'State after transition';
COMMENT ON COLUMN StateTransitionLog.transition_timestamp IS 'Timestamp of transition';
COMMENT ON COLUMN StateTransitionLog.triggering_agent_id IS 'Optional: Agent ID initiating change';
COMMENT ON COLUMN StateTransitionLog.triggering_user_id IS 'Optional: User ID initiating change';
COMMENT ON COLUMN StateTransitionLog.justification IS 'Reason/policy for state transition';
COMMENT ON CONSTRAINT fk_log_agent ON StateTransitionLog IS 'Ensures logs link to valid agent. Deletes logs if agent is deleted.';


-- Trigger function for state change logging (from subtask 1.4)
CREATE OR REPLACE FUNCTION log_agent_state_change()
RETURNS TRIGGER AS $$
DECLARE
    v_triggering_agent_id UUID;
    v_triggering_user_id VARCHAR(255);
    v_justification TEXT;
BEGIN
    -- Attempt to get trigger context from session variables (set by application)
    BEGIN v_triggering_agent_id := current_setting('myapp.triggering_agent_id', true)::UUID; EXCEPTION WHEN OTHERS THEN v_triggering_agent_id := NULL; END;
    BEGIN v_triggering_user_id := current_setting('myapp.triggering_user_id', true); EXCEPTION WHEN OTHERS THEN v_triggering_user_id := NULL; END;
    BEGIN v_justification := current_setting('myapp.transition_justification', true); EXCEPTION WHEN OTHERS THEN v_justification := 'State changed via direct update or unspecified mechanism.'; END;

    IF TG_OP = 'UPDATE' AND OLD.lifecycle_state IS DISTINCT FROM NEW.lifecycle_state THEN
        INSERT INTO StateTransitionLog (agent_id, previous_state, new_state, transition_timestamp, triggering_agent_id, triggering_user_id, justification)
        VALUES (NEW.unique_id, OLD.lifecycle_state, NEW.lifecycle_state, CURRENT_TIMESTAMP, v_triggering_agent_id, v_triggering_user_id, v_justification);
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO StateTransitionLog (agent_id, previous_state, new_state, transition_timestamp, triggering_agent_id, triggering_user_id, justification)
        VALUES (NEW.unique_id, NULL, NEW.lifecycle_state, CURRENT_TIMESTAMP, v_triggering_agent_id, v_triggering_user_id, v_justification);
    END IF;
    RETURN NEW; -- Return value is ignored for AFTER trigger, but required syntax
END;
$$ LANGUAGE plpgsql;

-- Trigger definition for state change logging (from subtask 1.4)
CREATE TRIGGER agents_state_change_trigger
AFTER INSERT OR UPDATE ON Agents
FOR EACH ROW
EXECUTE FUNCTION log_agent_state_change();

COMMENT ON TRIGGER agents_state_change_trigger ON Agents IS 'Automatically logs state changes to StateTransitionLog.';


-- Indexes (from subtask 1.5)

-- === Indexes for Agents table ===
CREATE INDEX idx_agents_type ON Agents(type);
COMMENT ON INDEX idx_agents_type IS 'Supports efficient filtering by agent type.';
CREATE INDEX idx_agents_lifecycle_state ON Agents(lifecycle_state);
COMMENT ON INDEX idx_agents_lifecycle_state IS 'Supports efficient filtering by agent lifecycle state.';
CREATE INDEX idx_agents_owner ON Agents(owner);
COMMENT ON INDEX idx_agents_owner IS 'Supports filtering agents by owner, useful for reporting.';
CREATE INDEX idx_agents_active_states ON Agents(lifecycle_state)
WHERE lifecycle_state NOT IN ('ARCHIVED', 'KILLED');
COMMENT ON INDEX idx_agents_active_states IS 'Partial index to efficiently find agents in non-terminal states.';

-- === Indexes for AgentMetadata table ===
CREATE INDEX idx_agentmetadata_agent_id ON AgentMetadata(agent_id);
COMMENT ON INDEX idx_agentmetadata_agent_id IS 'Supports efficiently finding all metadata for a specific agent.';
CREATE INDEX idx_agentmetadata_key ON AgentMetadata(key);
COMMENT ON INDEX idx_agentmetadata_key IS 'Supports finding specific metadata keys across different agents.';
CREATE INDEX idx_agentmetadata_value_gin ON AgentMetadata USING GIN (value);
COMMENT ON INDEX idx_agentmetadata_value_gin IS 'GIN index to support efficient querying within the JSONB value column.';

-- === Indexes for StateTransitionLog table ===
CREATE INDEX idx_log_agent_id ON StateTransitionLog(agent_id);
COMMENT ON INDEX idx_log_agent_id IS 'Supports efficiently retrieving the state transition history for a specific agent.';
CREATE INDEX idx_log_transition_timestamp ON StateTransitionLog(transition_timestamp);
COMMENT ON INDEX idx_log_transition_timestamp IS 'Supports time-based queries on state transition history.'; 