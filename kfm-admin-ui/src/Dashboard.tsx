import { Card, CardContent, CardHeader, Typography, Grid, CircularProgress, List, ListItem, ListItemText } from "@mui/material";
import { Title, useGetList, RaRecord, Identifier } from "react-admin";
import { Error } from "react-admin"; // Import Error component
import { useState, useEffect } from 'react'; // Import useState and useEffect

// Placeholder components for dashboard widgets
const AgentStateSummary = () => {
    const { data: agents, total, isLoading, error } = useGetList<RaRecord>('agents', { 
        pagination: { page: 1, perPage: 1000 } // Fetch all agents to count states
    }); 

    if (isLoading) { return <CircularProgress size={20} />; }
    if (error) { return <Typography color="error">Error loading agent states</Typography>; }
    if (!agents) { return <Typography>No agent data.</Typography>}

    // Count agents per state - Actual logic
    const statesCount = agents.reduce((acc, agent) => {
        const state = agent.state || 'UNKNOWN'; // Assuming agent has a 'state' field
        acc[state] = (acc[state] || 0) + 1;
        return acc;
    }, {} as Record<string, number>); 

    return (
        <Card sx={{ height: '100%' }}>
            <CardHeader title="Agent States" />
            <CardContent>
                {Object.entries(statesCount).map(([state, count]) => (
                    <Typography key={state}>{state}: {count}</Typography>
                ))}
                <Typography variant="body2" sx={{ mt: 1 }}>Total: {total ?? 0}</Typography>
                {/* TODO: Add a pie chart here later */}
            </CardContent>
        </Card>
    );
};

const RecentOperations = () => {
    // Assuming an 'auditlogs' resource exists for operations/events
    const { data: logs, total, isLoading, error } = useGetList<RaRecord>('auditlogs', { 
        pagination: { page: 1, perPage: 5 }, 
        sort: { field: 'timestamp', order: 'DESC' } // Sort by timestamp descending
    });

    if (isLoading) { return <CircularProgress size={20} />; }
    // Use the RaError component for better error display
    if (error) { return <Error error={error} />; } 
    if (!logs || logs.length === 0) { return <Typography>No recent operations.</Typography>; }

    return (
        <Card sx={{ height: '100%' }}>
            <CardHeader title="Recent KFM Operations" />
            <CardContent>
                <List dense disablePadding>
                    {logs.map(log => (
                        <ListItem key={log.id} disableGutters sx={{ pb: 0 }}>
                            <ListItemText 
                                primary={`${log.action || 'Unknown Action'} on ${log.entity_type || 'entity'} ${log.entity_id || ''}`} 
                                secondary={`${new Date(log.timestamp).toLocaleString()} by ${log.user_id || 'system'}`}
                                primaryTypographyProps={{ variant: 'body2' }}
                                secondaryTypographyProps={{ variant: 'caption' }}
                            />
                        </ListItem>
                    ))}
                </List>
            </CardContent>
        </Card>
    );
}

const SystemHealth = () => {
    // Placeholder - Real implementation would fetch from /health or similar
    const [healthData, setHealthData] = useState<Record<string, string>>({
        'API Gateway': 'Checking...',
        'Agent Registry': 'Checking...',
        'F Operator': 'Checking...',
        'K Operator': 'Checking...',
        'M Operator': 'Checking...',
        'Policy Engine': 'Checking...',
        'Resource Manager': 'Checking...'
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    // In a real scenario, you might use useDataProvider() and make custom calls
    useEffect(() => {
        // Simulate fetching health data
        setTimeout(() => {
            setHealthData({
                'API Gateway': 'Healthy',
                'Agent Registry': 'Healthy',
                'F Operator': 'Healthy',
                'K Operator': 'Warning', // Example status
                'M Operator': 'Healthy',
                'Policy Engine': 'Healthy',
                'Resource Manager': 'Error' // Example status
            });
            setLoading(false);
        }, 1500);
    }, []);

    const getStatusColor = (status: string) => {
        switch(status.toLowerCase()) {
            case 'healthy': return 'success.main';
            case 'warning': return 'warning.main';
            case 'error': return 'error.main';
            default: return 'text.secondary';
        }
    };

    return (
        <Card sx={{ height: '100%' }}>
            <CardHeader title="System Health" />
            <CardContent>
                {loading && <CircularProgress size={20} />}
                {error && <Typography color="error">Error loading health status</Typography>}
                {!loading && !error && Object.entries(healthData).map(([service, status]) => (
                    <Typography key={service} variant="body2">
                        {service}: <Typography component="span" variant="body2" sx={{ color: getStatusColor(status), fontWeight: 'bold' }}>{status}</Typography>
                    </Typography>
                ))}
            </CardContent>
        </Card>
    );
}

export const Dashboard = () => (
    <Grid container spacing={2} mt={1}>
        <Title title="KFM Dashboard" />
        <Grid item xs={12} md={4}>
            <AgentStateSummary />
        </Grid>
        <Grid item xs={12} md={4}>
            <RecentOperations />
        </Grid>
        <Grid item xs={12} md={4}>
            <SystemHealth />
        </Grid>
        <Grid item xs={12}>
            <Card>
                <CardHeader title="Agent Dependency Graph (Placeholder)" />
                <CardContent>
                    {/* <AgentDependencyGraph /> Component to be added here */}
                    <Typography>Dependency graph visualization will go here.</Typography>
                </CardContent>
            </Card>
        </Grid>
        {/* Add more dashboard widgets/rows as needed */}
    </Grid>
); 