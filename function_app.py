import azure.functions as func
import logging
import os
import json
from PIL import Image
import base64
from typing import List
import pandas as pd
from io import BytesIO
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_experimental.utilities import PythonREPL
from langchain_community.chat_message_histories import RedisChatMessageHistory


SERVER = os.environ["SQLSERVER"]
DATABASE = os.environ["SQLDATABASE"]
USERNAME = os.environ["SQLUSERNAME"]
PASSWORD = os.environ["SQLPASSWORD"]

connectionString = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'

brochure_image_url=""

code_gen_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            write a python code to query sql server tables below and always use the connectionString variable to connect to the sql server, but exclude the line of code that defines the connectionString variable.

                insurance 
                    [age] [tinyint] NOT NULL,
                    [sex] [nvarchar](50) NOT NULL,
                    [bmi] [float] NOT NULL,
                    [children] [tinyint] NOT NULL,
                    [smoker] [nvarchar](50) NOT NULL,
                    [region] [nvarchar](50) NOT NULL,
                    [charges] [float] NOT NULL

            if the question requries data from multiple table to answer the question join those tables using sql queries 
            if the search is by name make sure you conver the column to lower case before comparing and use like operator to search for the name in the query

            sample python code to connect to sql server and use the df from the claims data to join with the policy data:
            always print the result_df using pythin print command at the end of the code
            
            import pyodbc
            import pandas as pd
            # Connect to SQL Server
            conn = pyodbc.connect(connectionString)
            SQL_QUERY = '''
            SELECT
                *
            FROM
                insurance
            '''
            cursor = conn.cursor()
            cursor.execute(SQL_QUERY)
            records = cursor.fetchall()
            # Convert to pandas DataFrame
            columns = ['age','sex','bmi','children','smoker','region','charges']
            result_df = pd.DataFrame.from_records(records, columns=columns)
            conn.close()
            print(result_df)

            Here is the user question , conversation history and the connectionString to use in the code:""",
            
        ),
        ("placeholder", "{messages}"),
        ("placeholder", "{connectionString}")
    ]
)

file_upload_code_gen_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            write a python code to analysis the data 

            sample python code to connect to analyze the data from the uploaded file:
            use sample_data to determine the data type and columns in the file, and use csv_filename = 'output.csv' to get the actual data from the file to analyze and print the result_df at the end of the code.
            always print the result_df using python print command at the end of the code
            
            sample python code to analyze the data from the uploaded file:
            import pandas as pd
            csv_filename = 'output.csv'

            # Create a DataFrame from the CSV file
            data = pd.read_csv(csv_filename)
            
            # Select relevant columns for the result
            result_df = data[['property_id', 'property_name']]
            
            # Print the result
            print(result_df)

            Here is the user question :""",
        ),
        ("placeholder", "{messages}"),
    ]
)


visualize_data_code_gen_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Write a Python script to analyze the dataset and generate graphs or charts based on the provided data. The script must meet the following requirements:

            Use the data under sample_data section to understand the column names and data types.
            Use the CSV file named 'output.csv' as the actual dataset for analysis.
            Select relevant columns from the dataset to create meaningful visualizations using matplotlib.pyplot.
            Ensure the resulting plot is saved as an image file named 'image.png' using plt.savefig('image.png') python command. If an image.png file already exists, it should be overwritten.
            Do not print() in the code; simply save the chart 
           
            sample python code to analyze the data from the uploaded file:

            import pandas as pd
            import matplotlib.pyplot as plt

            # Define the CSV file name
            csv_filename = 'output.csv'

            # Load the data from the CSV file
            data = pd.read_csv(csv_filename)

            # Perform the desired analysis and select the relevant columns
            result_df = data[['Column1', 'Column2']]  # Replace with appropriate columns

            # Create the desired visualization
            result_df.plot(kind='bar', x='Column1', y='Column2')  # Customize the kind of plot
            plt.xlabel('Column1 Label')  # Replace with appropriate labels
            plt.ylabel('Column2 Label')
            plt.title('Title of the Graph')

            # Save the plot as "image.png"
            plt.savefig('image.png')
            Modify the analysis and plotting logic as necessary to answer specific user questions or focus on specific aspects of the dataset.

            Here is the user question :""",
        ),
        ("placeholder", "{messages}"),
    ]
)

# OpenAI Init
llm = AzureChatOpenAI(
        openai_api_version=os.environ["AZURE_OPENAI_VERSION"],
        openai_api_key=os.environ["AZURE_OPENAI_KEY"],
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        temperature = 0.1
    )

# Data model
class code(BaseModel):
    """Code output"""
    prefix: str = Field(description="Description of the problem and approach")
    imports: str = Field(description="Code block import statements")
    code: List = Field(description="Code block not including import statements")
    description = "Schema for code solutions to questions about LCEL."

code_gen_chain = code_gen_prompt | llm.with_structured_output(code)
file_upload_code_gen_prompt_chain = file_upload_code_gen_prompt | llm.with_structured_output(code)
visualize_data_code_gen_prompt_chain = visualize_data_code_gen_prompt | llm.with_structured_output(code)

repl = PythonREPL()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
@app.route(route="nl-to-sqldb")
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Analyze SQL DB data using NL - Python HTTP trigger function processed a request.')

    req_body = req.get_json()
    user_prompt = req_body.get('prompt')

    code_result = code_gen_chain.invoke({"messages": [("user", user_prompt)]})
    generated_code = "LLM Generated Code"+ "\n" +code_result.imports + "\n" + "\n".join(code_result.code)
    code_to_execute = "connectionString="+f'"{connectionString}"'+ "\n" +code_result.imports + "\n" + "\n".join(code_result.code)

    result = repl.run(code_to_execute)

    llm_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Your task is look at the resultset and respond in natural language to the user query.
            Here is the user question:""",
        ),
        ("placeholder", "{messages}")
    ]
    )

    # Data model
    class llm_response(BaseModel):
        """llm output"""
        resp: str = Field(description="llm response to the user query")

    ai_chain = llm_prompt | llm.with_structured_output(llm_response) 
    final_result = ai_chain.invoke({"messages": [("user", user_prompt + "resultset: "+ str(  result ))]})
    
    return func.HttpResponse(
          json.dumps({"generated_code": f"{generated_code}","code_result": f"{result}", "final_result": f"{final_result.resp}"}),
          status_code=200)

@app.route(route="nl_to_csv", auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger1(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Analyze CSV using NL - Python HTTP trigger function processed a request.')
    user_prompt = req.form.get('prompt')
    file = req.files.get('file')
    filestream = file.read()

    df = pd.read_csv(BytesIO(filestream))

    # Save the DataFrame as a CSV file
    csv_filename = 'output.csv'
    df.to_csv(csv_filename, index=False)

    # Get the column names from the DataFrame to aid in code generation
    column_names = df.columns
    column_names_list = df.columns.tolist()
    
    code_result = file_upload_code_gen_prompt_chain.invoke({"messages": [("user", user_prompt + "\n" + "sample_data:" + "\n" + f'"{column_names_list}"' )]})
    generated_code = "LLM Generated Code"+ "\n" +code_result.imports + "\n" + "\n".join(code_result.code)
    code_to_execute =  code_result.imports + "\n" + "\n".join(code_result.code)

    result = repl.run(code_to_execute)
    print("-----RESULT---"+result)

    from langchain.memory import ChatMessageHistory

    llm_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Your task is look at the resultset and respond in natural language to the user query.
            Here is the user question:""",
        ),
        ("placeholder", "{messages}"),

    ]
    )
    
    # Data model
    class llm_response(BaseModel):
        """llm output"""
        resp: str = Field(description="llm response to the user query")


    ai_chain = llm_prompt | llm.with_structured_output(llm_response)
    final_result = ai_chain.invoke({"messages": [("user", user_prompt + "resultset: "+ result)]})

    return func.HttpResponse(
          json.dumps({"generated_code": f"{generated_code}","code_result": f"{result}", "final_result": f"{final_result.resp}"}),
          status_code=200)