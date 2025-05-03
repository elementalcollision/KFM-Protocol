import { Create, SimpleForm, TextInput, BooleanInput, required } from 'react-admin';
import { Grid, Box, Typography } from '@mui/material';

// Placeholder for a code editor component (reuse from Edit view or common component)
const CodeEditorInput = ({ source, label }: { source: string, label?: string }) => {
    return (
        <TextInput 
            source={source} 
            label={label || source} 
            multiline 
            fullWidth 
            minRows={10} 
            validate={required()} // Definition is required on create
            helperText="Enter policy definition in YAML or JSON format" 
        />
    );
};

export const PolicyCreate = () => (
    <Create title="Create New Policy">
        <SimpleForm>
            <Grid container spacing={2}>
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
    </Create>
); 