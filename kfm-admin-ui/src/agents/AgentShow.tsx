import { Show, SimpleShowLayout, TextField, ChipField, DateField, RaRecord } from 'react-admin';
import { Grid, Typography, Box } from '@mui/material';

const AgentTitle = () => {
    const record = RaRecord();
    return <span>Agent Details {record ? `- ${record.name}` : ''}</span>;
};

export const AgentShow = () => (
    <Show title={<AgentTitle />}>
        <SimpleShowLayout>
            <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                    <Typography variant="caption" display="block" gutterBottom>ID</Typography>
                    <TextField source="id" />
                </Grid>
                <Grid item xs={12} md={6}>
                    <Typography variant="caption" display="block" gutterBottom>Name</Typography>
                    <TextField source="name" />
                </Grid>
                <Grid item xs={12} md={6}>
                    <Typography variant="caption" display="block" gutterBottom>Type</Typography>
                    <TextField source="type" />
                </Grid>
                <Grid item xs={12} md={6}>
                    <Typography variant="caption" display="block" gutterBottom>Version</Typography>
                    <TextField source="version" />
                </Grid>
                <Grid item xs={12} md={6}>
                    <Typography variant="caption" display="block" gutterBottom>State</Typography>
                    <ChipField source="state" />
                </Grid>
                 <Grid item xs={12} md={6}>
                     <Typography variant="caption" display="block" gutterBottom>Owner</Typography>
                    <TextField source="owner" />
                </Grid>
                 <Grid item xs={12} md={6}>
                     <Typography variant="caption" display="block" gutterBottom>Maintainer</Typography>
                    <TextField source="maintainer" />
                </Grid>
                <Grid item xs={12} md={6}>
                    <Typography variant="caption" display="block" gutterBottom>Created At</Typography>
                    <DateField source="created_at" showTime />
                </Grid>
                <Grid item xs={12} md={6}>
                    <Typography variant="caption" display="block" gutterBottom>Updated At</Typography>
                    <DateField source="updated_at" showTime />
                </Grid>
                {/* Add other fields like description, capabilities (maybe ArrayField), metadata (maybe JsonField) */}
                <Grid item xs={12}>
                    <Typography variant="caption" display="block" gutterBottom>Description</Typography>
                    <TextField source="description" />
                </Grid>
                 {/* TODO: Add sections for related data like Metadata, Logs, Dependencies */}
            </Grid>
        </SimpleShowLayout>
    </Show>
); 