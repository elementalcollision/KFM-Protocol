// Neo4j Schema Setup: Constraints and Indexes for KFM-AE

// === Constraints ===

// Ensure unique_id is unique across all :Agent nodes (from subtask 1.6)
CREATE CONSTRAINT unique_agent_id IF NOT EXISTS FOR (a:Agent) REQUIRE a.unique_id IS UNIQUE;
COMMENT ON CONSTRAINT unique_agent_id IS 'Ensures each :Agent node has a unique unique_id property, linking it to the Postgres record.';

// === Indexes ===

// Index on unique_id for fast node lookup (from subtask 1.6)
// Note: Often created automatically with unique constraint, but explicit creation ensures it exists.
CREATE INDEX agent_unique_id_index IF NOT EXISTS FOR (a:Agent) ON (a.unique_id);
COMMENT ON INDEX agent_unique_id_index IS 'Supports fast lookup of Agent nodes by their unique_id.';

// Index on type (from subtask 1.6)
CREATE INDEX agent_type_index IF NOT EXISTS FOR (a:Agent) ON (a.type);
COMMENT ON INDEX agent_type_index IS 'Supports efficient filtering of Agent nodes by their type.';

// Index on status (from subtask 1.6)
CREATE INDEX agent_status_index IF NOT EXISTS FOR (a:Agent) ON (a.status);
COMMENT ON INDEX agent_status_index IS 'Supports efficient filtering of Agent nodes by their status (lifecycle_state).';

// Index on version (from subtask 1.6)
CREATE INDEX agent_version_index IF NOT EXISTS FOR (a:Agent) ON (a.version);
COMMENT ON INDEX agent_version_index IS 'Supports efficient lookup of Agent nodes by their version string.'; 