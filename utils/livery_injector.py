import aiohttp
import json
import logging
import asyncio
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class LiveryInjector:
    def __init__(self):
        self.base_url = "https://be38c.playfabapi.com/Client/ExecuteCloudScript"
        self.params = "?sdk=UnitySDK-2.212.250428&engine=6000.1.5f1&platform=Android"
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def add_livery(self, item_id: str, auth_token: str) -> Tuple[bool, Dict]:
        url = self.base_url + self.params
        
        headers = {
            'User-Agent': "UnityPlayer/6000.1.5f1 (UnityWebRequest/1.0, libcurl/8.10.1-DEV)",
            'Accept-Encoding': "deflate, gzip",
            'Content-Type': "application/json",
            'X-ReportErrorAsSuccess': "true",
            'X-PlayFabSDK': "UnitySDK-2.212.250428",
            'X-Authorization': auth_token,
            'X-Unity-Version': "6000.1.5f1"
        }
        
        livery_name = await self.get_livery_name(item_id)
        logger.info(f"Starting livery injection for {livery_name}")
        
        payload_1 = {
            "CustomTags": None,
            "FunctionName": "ExecuteGrantItems",
            "FunctionParameter": {"itemIds": [item_id]},
            "GeneratePlayStreamEvent": False
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, data=json.dumps(payload_1), headers=headers) as response:
                    if response.status != 200:
                        return False, {"error": f"HTTP {response.status}: {await response.text()}"}
                    
                    response_1_data = await response.json()
                
                item_instance_id, extracted_item_id = await self._extract_item_data(response_1_data.get('data', {}).get('FunctionResult', {}), item_id)
                
                if not item_instance_id:
                    return False, {"error": "Missing itemInstanceId", "response1": response_1_data}
                
                logger.info(f"Extracted instance ID: {item_instance_id}")
                
                payload_2 = {
                    "CustomTags": None,
                    "FunctionName": "UploadCustomDataWithItem",
                    "FunctionParameter": {
                        "itemInstanceId": item_instance_id,
                        "itemId": extracted_item_id or item_id
                    },
                    "GeneratePlayStreamEvent": False
                }
                
                await asyncio.sleep(2)
                
                async with session.post(url, data=json.dumps(payload_2), headers=headers) as response:
                    if response.status != 200:
                        return False, {"error": f"HTTP {response.status} on second request: {await response.text()}"}
                    
                    response_2_data = await response.json()
                
                return True, {
                    "response1": response_1_data,
                    "response2": response_2_data,
                    "itemInstanceId": item_instance_id,
                    "itemId": extracted_item_id or item_id,
                    "liveryName": livery_name
                }
                
        except asyncio.TimeoutError:
            return False, {"error": "Request timeout"}
        except aiohttp.ClientError as e:
            return False, {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return False, {"error": f"Unexpected error: {str(e)}"}
    
    async def _extract_item_data(self, function_result: Dict, default_item_id: str) -> Tuple[Optional[str], Optional[str]]:
        item_instance_id = None
        extracted_item_id = None
        
        try:
            if 'grantedItems' in function_result:
                gi = function_result['grantedItems']
                if gi and len(gi) > 0:
                    item_instance_id = gi[0].get('ItemInstanceId')
                    extracted_item_id = gi[0].get('ItemId')
            elif 'ItemGrantResults' in function_result:
                igr = function_result['ItemGrantResults']
                if igr and len(igr) > 0:
                    item_instance_id = igr[0].get('ItemInstanceId')
                    extracted_item_id = igr[0].get('ItemId')
            elif 'itemInstanceId' in function_result:
                item_instance_id = function_result.get('itemInstanceId')
                extracted_item_id = function_result.get('itemId', default_item_id)
            
            return item_instance_id, extracted_item_id
        except Exception as e:
            logger.error(f"Error extracting item data: {e}")
            return None, None
    
    async def get_livery_name(self, livery_id: str) -> str:
        from utils.livery_service import LiveryService
        livery_service = LiveryService()
        return livery_service.get_livery_info(livery_id) or f"Livery {livery_id}"
    
    async def validate_auth_token(self, auth_token: str) -> Tuple[bool, Optional[str]]:
        url = self.base_url + self.params
        
        headers = {
            'User-Agent': "UnityPlayer/6000.1.5f1 (UnityWebRequest/1.0, libcurl/8.10.1-DEV)",
            'Accept-Encoding': "deflate, gzip",
            'Content-Type': "application/json",
            'X-ReportErrorAsSuccess': "true",
            'X-PlayFabSDK': "UnitySDK-2.212.250428",
            'X-Authorization': auth_token,
            'X-Unity-Version': "6000.1.5f1"
        }
        
        payload = {
            "CustomTags": None,
            "FunctionName": "GetUserData",
            "FunctionParameter": {"Keys": ["profile"]},
            "GeneratePlayStreamEvent": False
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, data=json.dumps(payload), headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        playfab_id = data.get('data', {}).get('PlayFabId')
                        return True, playfab_id
                    else:
                        return False, None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False, None