import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import dash.exceptions

# Sample user data
users = {
    "admin": {"password": "admin123", "role": "Supervisor"},
    "employee1": {"password": "emp123", "role": "Employee"}
}

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # for deployment

# Login page layout
login_layout = dbc.Container([
    html.H2("Login Page", className="mb-4"),
    dbc.Input(id="user-id", placeholder="User ID", type="text", className="mb-2"),
    dbc.Input(id="password", placeholder="Password", type="password", className="mb-2"),
    dbc.Select(
        id="role",
        options=[
            {"label": "Supervisor", "value": "Supervisor"},
            {"label": "Employee", "value": "Employee"}
        ],
        placeholder="Select Role",
        className="mb-3"
    ),
    dbc.Button("Login", id="login-btn", color="primary", className="mb-2"),
    html.Div(id="login-output", className="text-danger")
], className="mt-5")

# Supervisor page layout
supervisor_layout = html.Div([
    html.H2("Welcome, Supervisor!"),
    dbc.Button("Logout", id="logout-btn-supervisor", color="danger", className="mt-3")
])

# Employee page layout
employee_layout = html.Div([
    html.H2("Welcome, Employee!"),
    dbc.Button("Logout", id="logout-btn-employee", color="danger", className="mt-3")
])

# App layout with URL routing
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# Handle page routing
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/supervisor":
        return supervisor_layout
    elif pathname == "/employee":
        return employee_layout
    else:
        return login_layout  # Default: show login page

# Login validation
@app.callback(
    Output("url", "pathname"),
    Output("login-output", "children"),
    Input("login-btn", "n_clicks"),
    State("user-id", "value"),
    State("password", "value"),
    State("role", "value"),
    prevent_initial_call=True
)
def validate_login(n_clicks, user_id, password, role):
    if n_clicks is None:
        raise dash.exceptions.PreventUpdate

    if not user_id or not password or not role:
        return dash.no_update, "Please fill in all fields."

    user = users.get(user_id)
    if user and user["password"] == password and user["role"] == role:
        if role == "Supervisor":
            return "/supervisor", ""
        elif role == "Employee":
            return "/employee", ""

    return dash.no_update, "Invalid credentials or role mismatch."

# Logout from supervisor page
@app.callback(
    Output("url", "pathname"),
    Input("logout-btn-supervisor", "n_clicks"),
    prevent_initial_call=True
)
def logout_supervisor(n_clicks):
    return "/"

# Logout from employee page
@app.callback(
    Output("url", "pathname"),
    Input("logout-btn-employee", "n_clicks"),
    prevent_initial_call=True
)
def logout_employee(n_clicks):
    return "/"

# Run app
if __name__ == "__main__":
    app.run_server(debug=True)
