import { Edit, SimpleForm, TextInput, BooleanInput, required, RaRecord } from 'react-admin';
import { Grid, Box, Typography } from '@mui/material';

// Placeholder for a code editor component (e.g., using react-ace or similar)
const CodeEditorInput = ({ source, label }: { source: string, label?: string }) => {
    // In a real implementation, this would render a code editor
    return (
        <TextInput 
            source={source} 
            label={label || source} 
            multiline 
            fullWidth 
            minRows={10} 
            helperText="Enter policy definition in YAML or JSON format" 
        />
    );
};

const PolicyTitle = () => {
    const record = RaRecord();
    return <span>Policy {record ? `"${record.name}"` : ''}</span>;
};

export const PolicyEdit = () => (
    <Edit title={<PolicyTitle />}>
        <SimpleForm>
            <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                    <TextInput source="id" disabled fullWidth />
                </Grid>
                <Grid item xs={12} md={6}>
                    <TextInput source="name" validate={required()} fullWidth />
                </Grid>
                <Grid item xs={12}>
                    <TextInput source="description" multiline fullWidth />
                </Grid>
                <Grid item xs={12} md={6}>
                    <BooleanInput source="enabled" defaultValue={true} />
                </Grid>
                 <Grid item xs={12}>
                    <Box mt={2}>
                        <Typography variant="h6" gutterBottom>Policy Definition</Typography>
                        <CodeEditorInput source="definition" /> 
                        {/* TODO: Add validation based on policy schema */}
                    </Box>
                </Grid>
            </Grid>
        </SimpleForm>
    </Edit>
); 