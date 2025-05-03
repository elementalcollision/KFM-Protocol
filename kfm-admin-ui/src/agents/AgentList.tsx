import { List, Datagrid, TextField, ChipField, DateField, EditButton } from 'react-admin';

export const AgentList = () => (
    <List>
        <Datagrid rowClick="show"> {/* Or rowClick="edit" */}
            <TextField source="id" />
            <TextField source="name" />
            <TextField source="type" />
            <TextField source="version" />
            {/* Assuming 'state' is a field in your agent data */}
            <ChipField source="state" /> 
            <DateField source="created_at" label="Created" showTime />
            <DateField source="updated_at" label="Updated" showTime />
            <EditButton />
            {/* Add custom action buttons later */}
        </Datagrid>
    </List>
); 