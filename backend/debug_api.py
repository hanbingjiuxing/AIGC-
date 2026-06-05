
import requests

BASE_URL = 'http://127.0.0.1:5000/api'

def debug_members():
    # 1. Login
    try:
        print("Logging in as teacher...")
        resp = requests.post(f'{BASE_URL}/auth/login', json={'account': 'teacher', 'password': '123456'})
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} {resp.text}")
            return
        
        token = resp.json()['token']
        print(f"Login successful. Token: {token[:10]}...")
        
        # 2. Get Members
        print("Fetching members...")
        headers = {'Authorization': f'Bearer {token}'}
        resp = requests.get(f'{BASE_URL}/members', headers=headers)
        
        if resp.status_code != 200:
            print(f"Get members failed: {resp.status_code} {resp.text}")
            return
            
        data = resp.json()
        print(f"Members response keys: {data.keys()}")
        if 'members' in data:
            print(f"First member keys: {data['members'][0].keys() if data['members'] else 'No members'}")
            print(f"First member sample: {data['members'][0] if data['members'] else ''}")
        else:
            print("ERROR: 'members' key missing in response")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == '__main__':
    debug_members()
