from web3 import AsyncWeb3, AsyncHTTPProvider, Web3
from eth_utils import to_checksum_address
from typing import List, Dict, Tuple
import json
import asyncio
from collections import defaultdict
from web3.middleware import async_geth_poa_middleware
from datetime import datetime, timezone
from loguru import logger

logger.add('debug.log', format='{time},{level},{message}', level='DEBUG')
class TokenBalanceTracker:
    """
    A class to track ERC-20 token balances on the Polygon (MATIC) blockchain.
    """

    TRANSFER_EVENT_SIGNATURE: str

    def __init__(self, rpc_url: str, contract_address: str, abi_path: str):
        """
        Initialize the TokenBalanceTracker class.

        :param rpc_url: URL of the RPC server.
        :param contract_address: Address of the ERC-20 token contract.
        :param abi_path: Path to the contract ABI file.
        """
        self.web3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.contract_address = to_checksum_address(contract_address)
        self.contract = self.web3.eth.contract(address=self.contract_address, abi=self._load_abi(abi_path))
        self.TRANSFER_EVENT_SIGNATURE = Web3.keccak(text='Transfer(address,address,uint256)').hex()

    def _load_abi(self, abi_path: str) -> Dict:
        """
        Load the contract ABI from a file.

        :param abi_path: Path to the ABI file.
        :return: The contract ABI.
        """
        with open(abi_path) as f:
            return json.load(f)

    async def get_transfer_events(self, start_block: int, end_block: int) -> List[Dict]:
        """
        Retrieve Transfer events from a range of blocks.

        :param start_block: The starting block number.
        :param end_block: The ending block number.
        :return: A list of Transfer event logs.
        """
        try:
            logs = await self.web3.eth.get_logs({
                'fromBlock': start_block,
                'toBlock': end_block,
                'address': self.contract_address,
                'topics': [self.TRANSFER_EVENT_SIGNATURE]
            })
            return logs
        except Exception as e:
            logger.error(f"Error fetching logs from block {start_block} to {end_block}: {e}")
            raise

    async def get_all_transfer_events(self) -> List[Dict]:
        """
        Retrieve all Transfer events from the latest block to the block 1,000,000 blocks ago.

        :return: A list of all Transfer events.
        """
        latest_block = await self.get_last_block()
        all_events = []
        BLOCK_RANGE = 50000
        start_block = latest_block
        end_block_limit = max(latest_block - 1000000, 0)  # Limiting to the block 1,000,000 blocks ago

        tasks = []

        while start_block > end_block_limit:
            end_block = max(start_block - BLOCK_RANGE + 1, end_block_limit)
            tasks.append(self.get_transfer_events(end_block, start_block))
            start_block = end_block - 1

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error fetching logs: {result}")
            else:
                all_events.extend(result)

        return all_events

    async def calculate_balances(self, events: List[Dict]) -> Dict[str, int]:
        """
        Calculate token balances based on Transfer events.

        :param events: A list of Transfer event logs.
        :return: A dictionary with addresses as keys and balances as values.
        """
        balances = defaultdict(int)

        for event in events:
            from_address = '0x' + event['topics'][1].hex()[26:]
            to_address = '0x' + event['topics'][2].hex()[26:]
            value = int(event['data'].hex(), 16)

            if from_address != '0x0000000000000000000000000000000000000000':
                balances[from_address] -= value
            if to_address != '0x0000000000000000000000000000000000000000':
                balances[to_address] += value

        return balances

    async def get_top_balances(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Retrieve the top token balances.

        :param top_n: The number of top addresses to return.
        :return: A list of tuples containing addresses and their balances, sorted in descending order.
        """
        events = await self.get_all_transfer_events()
        balances = await self.calculate_balances(events)

        sorted_balances = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return sorted_balances

    async def get_last_block(self) -> int:
        """
        Retrieve the latest block number.

        :return: The latest block number.
        """
        last_block = await self.web3.eth.block_number
        return last_block

    async def get_last_transaction_date(self, address: str) -> str:
        """
        Get the date of the last transaction for a specific address.

        :param address: The address to check.
        :return: The date of the last transaction in ISO format.
        """
        latest_block = await self.get_last_block()
        BLOCK_RANGE = 50000
        start_block = latest_block
        end_block_limit = max(latest_block - 1000000, 0)  # Limiting to the block 1,000,000 blocks ago

        last_transaction_block = None

        while start_block > end_block_limit:
            end_block = max(start_block - BLOCK_RANGE + 1, end_block_limit)
            try:
                logs = await self.get_transfer_events(end_block, start_block)
                for log in logs:
                    from_address = '0x' + log['topics'][1].hex()[26:]
                    to_address = '0x' + log['topics'][2].hex()[26:]
                    if address in (from_address, to_address):
                        last_transaction_block = max(last_transaction_block or 0, log['blockNumber'])
            except Exception as e:
                logger.error(f"Error fetching logs from block {end_block} to {start_block}: {e}")
                break

            start_block = end_block - 1

        if last_transaction_block:
            try:
                block_info = await self.web3.eth.get_block(last_transaction_block)
                # Use timezone-aware datetime objects
                return datetime.fromtimestamp(block_info['timestamp'], timezone.utc).isoformat()
            except Exception as e:
                logger.error(f"Error fetching block info: {e}")
                return 'N/A'
        return 'N/A'

    async def get_top_balances_with_dates(self, top_n: int = 10) -> List[Tuple[str, int, str]]:
        """
        Retrieve the top token balances with the date of the last transaction.

        :param top_n: The number of top addresses to return.
        :return: A list of tuples containing address, balance, and last transaction date.
        """
        top_balances = await self.get_top_balances(top_n)
        tasks = [self.get_last_transaction_date(address) for address, _ in top_balances]
        last_transaction_dates = await asyncio.gather(*tasks)

        results = [(address, balance, date) for (address, balance), date in zip(top_balances, last_transaction_dates)]
        return results

    async def get_balance(self, address: str):
        address = to_checksum_address(address)
        balance_wei = await self.contract.functions.balanceOf(address).call()
        decimals = await self.contract.functions.decimals().call()
        balance = balance_wei / 10 ** decimals
        symbol = await self.contract.functions.symbol().call()
        logger.info(symbol, balance_wei, balance)
        return balance_wei, balance

    async def get_balances_batch(self, addresses: List):
        result = []
        for address in addresses:
            address = to_checksum_address(address)
            balance_wei = await self.contract.functions.balanceOf(address).call()
            decimals = await self.contract.functions.decimals().call()
            balance = balance_wei / 10 ** decimals
            result.append(balance)
        return result
    async def get_token_info(self, address):
        abi = self._load_abi('abis/erc20.json')
        address = to_checksum_address(address)
        contract = self.web3.eth.contract(address=address,abi=abi)
        symbol = await contract.functions.symbol().call()
        name = await contract.functions.name().call()
        total_supply = await contract.functions.totalSupply().call()
        decimals = await contract.functions.decimals().call()
        total_supply_tokens = total_supply / 10 ** decimals
        return {'symbol':symbol,'name':name,'totalSupply':total_supply, "decimals": decimals, 'totalSupply_tokens': total_supply_tokens}

async def main():
    rpc_url = 'https://polygon-mainnet.infura.io/v3/edcb17ba2f524017b1192f0cad991fe5'
    contract_address = '0x1a9b54A3075119f1546C52cA0940551A6ce5d2D0'
    abi_path = 'abis/erc20.json'
    tracker = TokenBalanceTracker(rpc_url, contract_address, abi_path)
    tracker.web3.middleware_onion.inject(async_geth_poa_middleware, layer=0)
    block = await tracker.get_last_block()
    logger.info(block)
    balance = await tracker.get_balance('0x51f1774249Fc2B0C2603542Ac6184Ae1d048351d')
    logger.info(balance)
    addresses = ["0x51f1774249Fc2B0C2603542Ac6184Ae1d048351d", "0x4830AF4aB9cd9E381602aE50f71AE481a7727f7C"]
    balances = await tracker.get_balances_batch(addresses)
    logger.info(balances)
    top_balances = await tracker.get_top_balances()
    logger.info(top_balances)

    for address, balance in top_balances:
        logger.info(f"Address: {address}, Balance: {balance}")

    top_balances_with_dates = await tracker.get_top_balances_with_dates(5)
    for address, balance, date in top_balances_with_dates:
        logger.info(f"Address: {address}, Balance: {balance}, Date: {date}")

    token_info = await tracker.get_token_info('0x1a9b54A3075119f1546C52cA0940551A6ce5d2D0')
    print(token_info)

if __name__ == '__main__':
    asyncio.run(main())