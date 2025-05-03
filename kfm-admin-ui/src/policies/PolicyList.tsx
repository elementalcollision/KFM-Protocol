import { List, Datagrid, TextField, BooleanField, DateField, EditButton } from 'react-admin';

export const PolicyList = () => (
    <List>
        <Datagrid rowClick="edit">
            <TextField source="id" />
            <TextField source="name" />
            <TextField source="description" />
            <BooleanField source="enabled" />
            <DateField source="created_at" label="Created" showTime />
            <DateField source="updated_at" label="Updated" showTime />
            <EditButton />
        </Datagrid>
    </List>
); 