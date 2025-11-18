import requests
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class LiveryService:
    def __init__(self):
        self.liveries_db_url = "https://gist.githubusercontent.com/R3XBASE/b0b9dcde1994d25a5257d8ccfa0c7939/raw/livery_db.json"
        self.cars_liveries = {}
        self.liveries_database = {}
        self.load_liveries_database()
    
    def load_liveries_database(self):
        try:
            response = requests.get(self.liveries_db_url, timeout=10)
            response.raise_for_status()
            raw_data = response.json()
            
            self.cars_liveries = raw_data
            
            self.liveries_database = {}
            total_liveries = 0
            for car_code, car_data in raw_data.items():
                car_name = car_data.get('carName', 'Unknown Car')
                for livery in car_data.get('liveries', []):
                    livery_id = livery.get('id')
                    livery_name = livery.get('name')
                    price = livery.get('price', {}).get('MN', 0)
                    if livery_id and livery_name:
                        self.liveries_database[livery_id] = {
                            'name': livery_name,
                            'car_name': car_name,
                            'price': price,
                            'car_code': car_code
                        }
                        total_liveries += 1
            
            logger.info(f"Loaded {len(self.cars_liveries)} cars with {total_liveries} liveries")
            return True
        except Exception as e:
            logger.error(f"Error loading liveries database: {e}")
            return False
    
    def get_cars(self) -> Dict:
        return self.cars_liveries
    
    def get_car_data(self, car_code: str) -> Optional[Dict]:
        return self.cars_liveries.get(car_code)
    
    def get_livery_info(self, livery_id: str) -> str:
        livery_data = self.liveries_database.get(livery_id)
        if livery_data:
            return f"{livery_data['name']} for {livery_data['car_name']} (Price: {livery_data['price']} MN)"
        return f"Unknown Livery ({livery_id})"
    
    def get_livery_data(self, livery_id: str) -> Optional[Dict]:
        return self.liveries_database.get(livery_id)
    
    def search_liveries(self, query: str) -> List[Dict]:
        results = []
        query = query.lower()
        for livery_id, data in self.liveries_database.items():
            if query in data['name'].lower() or query in data['car_name'].lower():
                results.append({
                    'id': livery_id,
                    **data
                })
        return results
    
    async def inject_livery(self, livery_id: str, auth_token: str) -> tuple:
        from utils.livery_injector import LiveryInjector
        injector = LiveryInjector()
        return await injector.add_livery(livery_id, auth_token)
    
    async def validate_account(self, auth_token: str) -> tuple:
        from utils.livery_injector import LiveryInjector
        injector = LiveryInjector()
        return await injector.validate_auth_token(auth_token)