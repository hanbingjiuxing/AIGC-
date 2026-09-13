
import requests

BASE_URL = 'http://127.0.0.1:5000/api'

def debug_works():
    # 1. Login as Student
    print("\n--- 1. Login as Student ---")
    s_resp = requests.post(f'{BASE_URL}/auth/login', json={'account': 'student', 'password': '123456'})
    if s_resp.status_code != 200:
        print("Student login failed")
        return
    s_token = s_resp.json()['token']
    s_id = s_resp.json()['user']['id']
    print(f"Student ID: {s_id}")

    # 2. Upload Work (Mock)
    print("\n--- 2. Upload Work ---")
    files = {'file': ('test.png', b'fake image content')}
    s_headers = {'Authorization': f'Bearer {s_token}'}
    u_resp = requests.post(f'{BASE_URL}/works/upload', headers=s_headers, files=files, data={'title': 'Debug Upload'})
    if u_resp.status_code != 201:
        print(f"Upload failed: {u_resp.text}")
    else:
        print("Upload successful")

    # 3. Login as Teacher
    print("\n--- 3. Login as Teacher ---")
    t_resp = requests.post(f'{BASE_URL}/auth/login', json={'account': 'teacher', 'password': '123456'})
    t_token = t_resp.json()['token']
    
    # 4. Teacher View Student Works
    print(f"\n--- 4. Teacher fetching works for user_id={s_id} ---")
    t_headers = {'Authorization': f'Bearer {t_token}'}
    list_resp = requests.get(f'{BASE_URL}/works', headers=t_headers, params={'user_id': s_id})
    
    if list_resp.status_code == 200:
        works = list_resp.json()['works']
        print(f"Found {len(works)} works.")
        for w in works:
            print(f"- [ID: {w['id']}] {w['title']} (User ID: {w['userId']})")
    else:
        print(f"Fetch failed: {list_resp.text}")

if __name__ == '__main__':
    debug_works()
