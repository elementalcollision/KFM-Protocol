import { Admin, Resource, ListGuesser } from "react-admin";
import { Layout } from "./Layout";

// Placeholder imports - Replace with actual implementations later
import { dataProvider } from "./dataProvider"; 
import { authProvider } from "./authProvider";
// Import the Dashboard component
import { Dashboard } from "./Dashboard";
// Import Agent list component
import { AgentList } from "./agents/AgentList"; // Assuming it's in src/agents/
// Import Agent edit component
import { AgentEdit } from "./agents/AgentEdit";
// Import Agent create component
import { AgentCreate } from "./agents/AgentCreate";
// Import Agent show component
import { AgentShow } from "./agents/AgentShow";
// Import Policy list component
import { PolicyList } from "./policies/PolicyList"; // Assuming it's in src/policies/
// Import Policy edit component
import { PolicyEdit } from "./policies/PolicyEdit";
// Import Policy create component
import { PolicyCreate } from "./policies/PolicyCreate";

export const App = () => (
    <Admin 
        layout={Layout}
        dataProvider={dataProvider} // Add dataProvider
        authProvider={authProvider} // Add authProvider
        dashboard={Dashboard} // Add Dashboard component
        title="KFM Admin UI"
        disableTelemetry // Optional: Disable react-admin telemetry
    >
        {/* Define main resources - Use ListGuesser initially */}
        <Resource name="agents" list={AgentList} edit={AgentEdit} create={AgentCreate} show={AgentShow} />
        <Resource name="policies" list={PolicyList} edit={PolicyEdit} create={PolicyCreate} />
        {/* Add other resources like users, auditlogs later */}
    </Admin>
);
