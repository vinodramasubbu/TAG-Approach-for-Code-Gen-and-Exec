Azure Function Setup and Usage
Prerequisites
Azure Functions Core Tools
Python 3.8+
Visual Studio Code with the Azure Functions extension
Setup
Clone the repository:

Create a virtual environment:

Activate the virtual environment:

Windows:

macOS/Linux:

Install the required packages:

Configuration:

Ensure the local.settings.json file contains the necessary environment variables for connecting to the SQL database. Create or update the file with the following content:

Start the Azure Function:

Running the Function
HTTP Triggers
nl-to-sqldb Trigger:

Endpoint: http://localhost:7071/api/nl-to-sqldb

Method: POST

Content-Type: application/json

Body:

Description: This trigger processes a natural language query to analyze data from a SQL database. It generates and executes SQL queries based on the provided prompt and returns the result.

nl_to_csv Trigger:

Endpoint: http://localhost:7071/api/nl_to_csv

Method: POST

Content-Type: multipart/form-data

Body:

Description: This trigger processes a natural language query to analyze data from an uploaded CSV file. It generates and executes Python code to analyze the data and returns the result.

Additional Information
Logs:

Logs can be viewed in the terminal where the Azure Function is running.
Debugging:

Use the provided launch.json configuration to attach the debugger in Visual Studio Code.
For more detailed information, refer to the Azure Functions documentation.

