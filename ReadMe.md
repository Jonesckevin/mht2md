# mht2md.py

## Overview
`mht2md.py` is a Python script designed to convert MHT (MIME HTML) files to Markdown format. This tool simplifies the process of transforming into the Markdown format.

## Installation and Usage
You only need to run the script in the folder with 1 or more MHT files. The script will convert all MHT files in the folder to Markdown format. Each MHT file will be converted to a separate Markdown file in their own folder with the same name as the MHT file.

1. Clone the repository:
    ```sh
    git clone https://github.com/jonesckevin/mht2md.git
    ```
2. Navigate to the project directory:
    ```sh
    cd mht2md
    ```
3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```
4. Run the script with the following command:
    ```sh
    python3 mht2md.py

## Docker Webapp
## Docker-Run
    ```sh
    cd Docker_Build
    docker build mht2md .
    docker run 
    ```
    
## Docker Compose
    ```yaml
    services:
        mht2md:
          image: jonesckevin/mht2md:latest
          container_name: mht2md-webapp
          ports:
            - 5674:80
    ```
