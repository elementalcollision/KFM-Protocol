import { Edit, SimpleForm, TextInput, SelectInput, required, RaRecord } from 'react-admin';
import { Grid } from '@mui/material';

// Define choices for agent state if it's editable
// Adjust these based on your actual lifecycle states
const agentStateChoices = [
    { id: 'NEW', name: 'New' },
    { id: 'EXPERIMENTAL', name: 'Experimental' },
    { id: 'CANDIDATE', name: 'Candidate' },
    { id: 'STABLE', name: 'Stable' },
    { id: 'DEPRECATED', name: 'Deprecated' },
    { id: 'ARCHIVED', name: 'Archived' },
    { id: 'KILLED', name: 'Killed' },
];

const AgentTitle = () => {
    const record = RaRecord();
    return <span>Agent {record ? `"${record.name}"` : ''}</span>;
};

export const AgentEdit = () => (
    <Edit title={<AgentTitle />}>
        <SimpleForm>
            <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                    <TextInput source="id" disabled fullWidth />
                </Grid>
                <Grid item xs={12} md={6}>
                    <TextInput source="name" validate={required()} fullWidth />
                </Grid>
                <Grid item xs={12} md={6}>
                    <TextInput source="type" validate={required()} fullWidth />
                </Grid>
                <Grid item xs={12} md={6}>
                    <TextInput source="version" validate={required()} fullWidth />
                </Grid>
                <Grid item xs={12} md={6}>
                    {/* Make state read-only if managed by KFM operators, or editable if needed */}
                    {/* <SelectInput source="state" choices={agentStateChoices} validate={required()} fullWidth /> */}
                    <TextInput source="state" disabled label="Current State" fullWidth />
                </Grid>
                 <Grid item xs={12} md={6}>
                    <TextInput source="owner" fullWidth />
                </Grid>
                 <Grid item xs={12} md={6}>
                    <TextInput source="maintainer" fullWidth />
                </Grid>
                {/* Add other editable fields like description, capabilities (maybe as ArrayInput), metadata (maybe as JsonInput) */}
                <Grid item xs={12}>
                    <TextInput source="description" multiline fullWidth />
                </Grid>
            </Grid>
        </SimpleForm>
    </Edit>
); 