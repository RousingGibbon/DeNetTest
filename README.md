# Token Balance Tracker

A FastAPI server that interacts with an ERC-20 token on the Polygon (MATIC) blockchain. The server provides endpoints to retrieve token balances, top token holders, and additional token information.

## Project Structure

DeNetTest/
server.py # FastAPI server
main.py # TokenBalanceTracker class
abis/
erc20.json # ABI for the ERC-20 token

## Requirements

- Python 3.8+
- FastAPI
- Uvicorn
- Web3.py

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/yourproject.git
   cd yourproject

2. Create a virtual environment and install dependencies:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install fastapi[standard] web3

## Configuration
1. Update the main.py file with the following configurations or use mine:

    rpc_url: Polygon RPC URL
    contract_address: Address of the ERC-20 token contract
    abi_path: Path to the ABI file
    Running the Server
## Running the Server
1. To start the FastAPI server, use one of in-build command:
    ```bash
   fastapi dev server.py
   fastapi run server.py

This will start the server at http://localhost:8000.

## Endpoints
1. Follow http://localhost:8000/docs


    
